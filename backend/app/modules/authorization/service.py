"""Authorization checks. Always use database state, never client-supplied role/org claims."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import Candidate, Job, User
from app.models.enums import UserRole, UserStatus
from app.modules.authorization.policies import (
    CandidateVisibilityMode,
    candidate_opted_into_discovery,
    current_visibility_mode,
)
from app.modules.identity import audit
from app.modules.identity.repository import IdentityRepository


class AuthorizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = IdentityRepository(db)

    def require_active(self, user: User) -> User:
        if user.status != UserStatus.ACTIVE.value:
            raise ForbiddenError("This account cannot use authenticated endpoints.")
        return user

    def require_roles(self, user: User, *roles: str) -> User:
        self.require_active(user)
        if user.role not in roles:
            self._denied(user, resource_type="role", metadata={"required": list(roles), "actual": user.role})
            raise ForbiddenError("You do not have permission to access this resource.")
        return user

    def require_candidate_owner(self, user: User, candidate_id: uuid.UUID) -> Candidate:
        self.require_active(user)
        candidate = self.repo.get_candidate(candidate_id)
        if candidate is None:
            raise NotFoundError("Candidate not found.")
        if user.role == UserRole.CANDIDATE.value and candidate.user_id == user.id:
            return candidate
        self._denied(
            user,
            resource_type="candidate",
            resource_id=candidate_id,
            metadata={"reason": "not_owner"},
        )
        raise ForbiddenError("You do not have permission to access this candidate.")

    def require_org_member(self, user: User, organization_id: uuid.UUID) -> None:
        self.require_active(user)
        org = self.repo.get_organization(organization_id)
        if org is None:
            raise NotFoundError("Organization not found.")
        if user.role == UserRole.ADMIN.value:
            return
        if user.role != UserRole.RECRUITER.value:
            self._denied(user, resource_type="organization", resource_id=organization_id)
            raise ForbiddenError("You do not have permission to access this organization.")
        if self.repo.membership(user.id, organization_id) is None:
            self._denied(
                user,
                resource_type="organization",
                resource_id=organization_id,
                metadata={"reason": "not_member"},
            )
            raise ForbiddenError("You do not have permission to access this organization.")

    def require_job_org_access(self, user: User, job_id: uuid.UUID) -> Job:
        self.require_active(user)
        job = self.repo.get_job(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        self.require_org_member(user, job.organization_id)
        return job

    def recruiter_organization_ids(self, user: User) -> list[uuid.UUID]:
        return [row.organization_id for row in self.repo.memberships_for_user(user.id)]

    def can_recruiter_view_candidate(self, user: User, candidate: Candidate) -> bool:
        if user.role == UserRole.ADMIN.value:
            return True
        if user.role != UserRole.RECRUITER.value:
            return False
        mode = current_visibility_mode()
        if mode is CandidateVisibilityMode.SHARED_CAMPUS_POOL:
            return True
        org_ids = self.recruiter_organization_ids(user)
        if self.repo.candidate_applied_to_org(candidate.id, org_ids):
            return True
        if mode is CandidateVisibilityMode.APPLICANTS_AND_OPTED_IN and candidate_opted_into_discovery(
            candidate.preferences
        ):
            return True
        return False

    def require_recruiter_candidate_scope(self, user: User, candidate_id: uuid.UUID) -> Candidate:
        self.require_roles(user, UserRole.RECRUITER.value, UserRole.ADMIN.value)
        candidate = self.repo.get_candidate(candidate_id)
        if candidate is None:
            raise NotFoundError("Candidate not found.")
        if not self.can_recruiter_view_candidate(user, candidate):
            self._denied(
                user,
                resource_type="candidate",
                resource_id=candidate_id,
                metadata={"reason": "out_of_scope"},
            )
            raise ForbiddenError("This candidate is outside your organization's scope.")
        return candidate

    def _denied(
        self,
        user: User,
        *,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        audit.record_audit(
            self.db,
            action=audit.AUTHZ_DENIED,
            resource_type=resource_type,
            actor_user_id=user.id,
            resource_id=resource_id,
            metadata=metadata or {},
        )
        self.db.flush()
