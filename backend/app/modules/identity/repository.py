"""Database access for identity. SQL stays here, not in routers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditLog, Candidate, Job, Organization, OrganizationMember, RefreshSession, User
from app.models.enums import MembershipRole


class IdentityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User)
            .options(selectinload(User.candidate), selectinload(User.memberships))
            .where(User.email == email)
        )

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(
            select(User)
            .options(selectinload(User.candidate), selectinload(User.memberships))
            .where(User.id == user_id)
        )

    def add_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def add_candidate(self, candidate: Candidate) -> Candidate:
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def add_organization(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        return organization

    def organization_slug_taken(self, slug: str) -> bool:
        return self.db.scalar(select(Organization.id).where(Organization.slug == slug)) is not None

    def add_membership(self, member: OrganizationMember) -> OrganizationMember:
        self.db.add(member)
        self.db.flush()
        return member

    def add_refresh_session(self, session: RefreshSession) -> RefreshSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_refresh_session_by_hash(self, token_hash: str) -> RefreshSession | None:
        return self.db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))

    def list_family_sessions(self, family_id: str) -> list[RefreshSession]:
        return list(
            self.db.scalars(
                select(RefreshSession).where(
                    RefreshSession.session_metadata.contains({"family_id": family_id})
                )
            ).all()
        )

    def list_active_sessions(self, user_id: uuid.UUID) -> list[RefreshSession]:
        return list(
            self.db.scalars(
                select(RefreshSession).where(
                    RefreshSession.user_id == user_id,
                    RefreshSession.revoked_at.is_(None),
                )
            ).all()
        )

    def membership(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> OrganizationMember | None:
        return self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == organization_id,
            )
        )

    def memberships_for_user(self, user_id: uuid.UUID) -> list[OrganizationMember]:
        return list(
            self.db.scalars(select(OrganizationMember).where(OrganizationMember.user_id == user_id)).all()
        )

    def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        return self.db.scalar(select(Candidate).where(Candidate.id == candidate_id))

    def get_candidate_for_user(self, user_id: uuid.UUID) -> Candidate | None:
        return self.db.scalar(select(Candidate).where(Candidate.user_id == user_id))

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self.db.scalar(select(Job).where(Job.id == job_id))

    def get_organization(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.id == organization_id))

    def candidate_applied_to_org(self, candidate_id: uuid.UUID, organization_ids: list[uuid.UUID]) -> bool:
        if not organization_ids:
            return False
        from app.models import Application

        return (
            self.db.scalar(
                select(Application.id)
                .join(Job, Job.id == Application.job_id)
                .where(
                    Application.candidate_id == candidate_id,
                    Job.organization_id.in_(organization_ids),
                )
                .limit(1)
            )
            is not None
        )

    def list_audit_actions(self, action: str, limit: int = 50) -> list[AuditLog]:
        return list(
            self.db.scalars(
                select(AuditLog)
                .where(AuditLog.action == action)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            ).all()
        )


def new_membership(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = MembershipRole.OWNER.value,
) -> OrganizationMember:
    return OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        membership_role=role,
    )
