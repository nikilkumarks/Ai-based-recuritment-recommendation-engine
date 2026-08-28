"""Identity application logic. Routers stay thin; SQL stays in the repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, UnauthenticatedError
from app.models import Candidate, Organization, RefreshSession, User
from app.models.enums import MembershipRole, OrganizationStatus, UserRole, UserStatus
from app.modules.identity import audit
from app.modules.identity.cookies import slugify_organization
from app.modules.identity.csrf import csrf_tokens_match, hash_csrf
from app.modules.identity.password import consume_password_check, hash_password, validate_password
from app.modules.identity.repository import IdentityRepository, new_membership
from app.modules.identity.tokens import (
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_token,
    refresh_expiry,
    utcnow,
)

GENERIC_AUTH_FAILURE = "Invalid email or password."
INACTIVE_ACCOUNT = "This account cannot sign in."


@dataclass(frozen=True)
class IssuedSession:
    user: User
    access_token: str
    refresh_token: str
    csrf_token: str
    expires_in: int
    refresh_max_age: int


class IdentityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = IdentityRepository(db)

    def register(
        self,
        *,
        email: str,
        password: str,
        role: str,
        organization_name: str | None,
    ) -> User:
        if role == UserRole.ADMIN.value:
            raise ForbiddenError("Admin accounts cannot be self-registered.")
        if role not in {UserRole.CANDIDATE.value, UserRole.RECRUITER.value}:
            raise ForbiddenError("Role is not allowed for registration.")
        validate_password(password, email)

        if self.repo.get_user_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        try:
            with self.db.begin_nested():
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    status=UserStatus.ACTIVE.value,
                )
                self.repo.add_user(user)

                if role == UserRole.CANDIDATE.value:
                    candidate = self.repo.add_candidate(Candidate(user_id=user.id))
                    user.candidate = candidate

                if role == UserRole.RECRUITER.value:
                    assert organization_name is not None
                    org = Organization(
                        name=organization_name,
                        slug=self._unique_org_slug(organization_name),
                        status=OrganizationStatus.ACTIVE.value,
                    )
                    self.repo.add_organization(org)
                    self.repo.add_membership(
                        new_membership(
                            organization_id=org.id,
                            user_id=user.id,
                            role=MembershipRole.OWNER.value,
                        )
                    )
        except IntegrityError as exc:
            raise ConflictError("An account with this email already exists.") from exc

        audit.record_audit(
            self.db,
            action=audit.REGISTER,
            resource_type="user",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={"role": user.role},
        )
        self.db.flush()
        return user

    def login(self, *, email: str, password: str) -> IssuedSession:
        user = self.repo.get_user_by_email(email)
        password_ok = consume_password_check(password, user.password_hash if user else None)
        if user is None or not password_ok:
            audit.record_audit(
                self.db,
                action=audit.LOGIN_FAILURE,
                resource_type="user",
                actor_user_id=user.id if user is not None else None,
                resource_id=user.id if user is not None else None,
                metadata={"reason": "invalid_credentials"},
            )
            self.db.flush()
            raise UnauthenticatedError(GENERIC_AUTH_FAILURE)

        if user.status != UserStatus.ACTIVE.value:
            audit.record_audit(
                self.db,
                action=audit.LOGIN_FAILURE,
                resource_type="user",
                actor_user_id=user.id,
                resource_id=user.id,
                metadata={"reason": "inactive", "status": user.status},
            )
            self.db.flush()
            raise ForbiddenError(INACTIVE_ACCOUNT)

        session = self._issue_session(user, family_id=str(uuid.uuid4()))
        user.last_login_at = utcnow()
        audit.record_audit(
            self.db,
            action=audit.LOGIN_SUCCESS,
            resource_type="user",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={},
        )
        self.db.flush()
        return session

    def refresh(self, *, raw_refresh_token: str | None, csrf_token: str | None) -> IssuedSession:
        session_row = self._load_valid_session(raw_refresh_token, csrf_token, reuse_check=True)
        user = self.repo.get_user_by_id(session_row.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            session_row.revoked_at = utcnow()
            self.db.flush()
            raise UnauthenticatedError("Invalid or expired refresh session.")

        family_id = str(session_row.session_metadata.get("family_id") or uuid.uuid4())
        session_row.revoked_at = utcnow()
        issued = self._issue_session(user, family_id=family_id)
        audit.record_audit(
            self.db,
            action=audit.REFRESH,
            resource_type="refresh_session",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={},
        )
        self.db.flush()
        return issued

    def logout(self, *, raw_refresh_token: str | None, csrf_token: str | None) -> None:
        session_row = self._load_valid_session(raw_refresh_token, csrf_token, reuse_check=False)
        session_row.revoked_at = utcnow()
        audit.record_audit(
            self.db,
            action=audit.LOGOUT,
            resource_type="refresh_session",
            actor_user_id=session_row.user_id,
            resource_id=session_row.id,
            metadata={},
        )
        self.db.flush()

    def logout_all(self, *, user: User) -> int:
        now = utcnow()
        sessions = self.repo.list_active_sessions(user.id)
        for row in sessions:
            row.revoked_at = now
        audit.record_audit(
            self.db,
            action=audit.LOGOUT_ALL,
            resource_type="user",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={"revoked_sessions": len(sessions)},
        )
        self.db.flush()
        return len(sessions)

    def _issue_session(self, user: User, *, family_id: str) -> IssuedSession:
        settings = get_settings()
        raw_refresh = generate_refresh_token()
        csrf_token = generate_csrf_token()
        access_token, access_expires = create_access_token(user_id=user.id, role=user.role)
        row = RefreshSession(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=refresh_expiry(),
            session_metadata={
                "family_id": family_id,
                "csrf_hash": hash_csrf(csrf_token),
            },
        )
        self.repo.add_refresh_session(row)
        refresh_max_age = int(timedelta(days=settings.refresh_token_expire_days).total_seconds())
        expires_in = int((access_expires - utcnow()).total_seconds())
        return IssuedSession(
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh,
            csrf_token=csrf_token,
            expires_in=max(expires_in, 1),
            refresh_max_age=refresh_max_age,
        )

    def _load_valid_session(
        self,
        raw_refresh_token: str | None,
        csrf_token: str | None,
        *,
        reuse_check: bool,
    ) -> RefreshSession:
        if not raw_refresh_token:
            raise UnauthenticatedError("Invalid or expired refresh session.")
        token_hash_value = hash_token(raw_refresh_token)
        row = self.repo.get_refresh_session_by_hash(token_hash_value)
        if row is None:
            raise UnauthenticatedError("Invalid or expired refresh session.")

        now = utcnow()
        if row.revoked_at is not None:
            if reuse_check:
                self._revoke_family(row)
            raise UnauthenticatedError("Invalid or expired refresh session.")
        if row.expires_at <= now:
            row.revoked_at = now
            self.db.flush()
            raise UnauthenticatedError("Invalid or expired refresh session.")

        stored_csrf = str(row.session_metadata.get("csrf_hash") or "")
        if csrf_token is not None and not csrf_tokens_match(csrf_token, stored_csrf):
            raise ForbiddenError("CSRF token was missing or invalid.")
        return row

    def _revoke_family(self, row: RefreshSession) -> None:
        family_id = row.session_metadata.get("family_id")
        if not family_id:
            return
        now = utcnow()
        for member in self.repo.list_family_sessions(str(family_id)):
            if member.revoked_at is None:
                member.revoked_at = now
        self.db.flush()

    def _unique_org_slug(self, name: str) -> str:
        base = slugify_organization(name)
        slug = base
        suffix = 0
        while self.repo.organization_slug_taken(slug):
            suffix += 1
            slug = f"{base}-{suffix}"
        return slug
