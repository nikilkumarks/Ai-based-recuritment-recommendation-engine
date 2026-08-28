"""FastAPI dependencies for RBAC, org membership, and resource ownership."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Candidate, Job, User
from app.modules.authorization.service import AuthorizationService
from app.modules.identity.dependencies import get_current_active_user


def get_authorization_service(db: Session = Depends(get_db)) -> AuthorizationService:
    return AuthorizationService(db)


def require_role(*roles: str) -> Callable[..., User]:
    def dependency(
        user: User = Depends(get_current_active_user),
        authz: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        return authz.require_roles(user, *roles)

    return dependency


def require_candidate_role(user: User = Depends(require_role("candidate"))) -> User:
    return user


def require_recruiter_role(user: User = Depends(require_role("recruiter"))) -> User:
    return user


def require_admin_role(user: User = Depends(require_role("admin"))) -> User:
    return user


def require_candidate_owner(candidate_id: uuid.UUID) -> Callable[..., Candidate]:
    def dependency(
        user: User = Depends(get_current_active_user),
        authz: AuthorizationService = Depends(get_authorization_service),
    ) -> Candidate:
        return authz.require_candidate_owner(user, candidate_id)

    return dependency


def require_org_member(organization_id: uuid.UUID) -> Callable[..., User]:
    def dependency(
        user: User = Depends(get_current_active_user),
        authz: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        authz.require_org_member(user, organization_id)
        return user

    return dependency


def CandidateOwnerDep(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    authz: AuthorizationService = Depends(get_authorization_service),
) -> Candidate:
    return authz.require_candidate_owner(user, candidate_id)


def OrgMemberDep(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    authz: AuthorizationService = Depends(get_authorization_service),
) -> User:
    authz.require_org_member(user, organization_id)
    return user


def JobOrgDep(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    authz: AuthorizationService = Depends(get_authorization_service),
) -> Job:
    return authz.require_job_org_access(user, job_id)


def RecruiterCandidateScopeDep(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    authz: AuthorizationService = Depends(get_authorization_service),
) -> Candidate:
    return authz.require_recruiter_candidate_scope(user, candidate_id)
