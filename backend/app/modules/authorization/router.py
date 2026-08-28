"""Authorization probes only. These are not recruitment, matching, or resume APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.models import Candidate, Job, User
from app.modules.authorization.dependencies import (
    CandidateOwnerDep,
    JobOrgDep,
    OrgMemberDep,
    RecruiterCandidateScopeDep,
    require_admin_role,
    require_candidate_role,
    require_recruiter_role,
)
from app.modules.identity.schemas import AuthzProbeResponse

router = APIRouter(prefix="/authz", tags=["authorization"])


@router.get("/candidate", response_model=AuthzProbeResponse)
def candidate_role_probe(user: User = Depends(require_candidate_role)) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="role", role=user.role)


@router.get("/recruiter", response_model=AuthzProbeResponse)
def recruiter_role_probe(user: User = Depends(require_recruiter_role)) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="role", role=user.role)


@router.get("/admin", response_model=AuthzProbeResponse)
def admin_role_probe(user: User = Depends(require_admin_role)) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="role", role=user.role)


@router.get("/candidates/{candidate_id}", response_model=AuthzProbeResponse)
def candidate_owner_probe(
    candidate_id: uuid.UUID,
    candidate: Candidate = Depends(CandidateOwnerDep),
    user: User = Depends(require_candidate_role),
) -> AuthzProbeResponse:
    return AuthzProbeResponse(
        resource_type="candidate",
        resource_id=candidate.id,
        role=user.role,
    )


@router.get("/organizations/{organization_id}", response_model=AuthzProbeResponse)
def org_member_probe(
    organization_id: uuid.UUID,
    user: User = Depends(OrgMemberDep),
) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="organization", resource_id=organization_id, role=user.role)


@router.get("/jobs/{job_id}", response_model=AuthzProbeResponse)
def job_org_probe(
    job_id: uuid.UUID,
    job: Job = Depends(JobOrgDep),
    user: User = Depends(require_recruiter_role),
) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="job", resource_id=job.id, role=user.role)


@router.get("/jobs/{job_id}/decisions", response_model=AuthzProbeResponse)
def job_decisions_probe(
    job_id: uuid.UUID,
    job: Job = Depends(JobOrgDep),
    user: User = Depends(require_recruiter_role),
) -> AuthzProbeResponse:
    """Authorization only — recruiter decisions are not listed in this phase."""
    return AuthzProbeResponse(resource_type="recruiter_decisions", resource_id=job.id, role=user.role)


@router.get("/candidates/{candidate_id}/recruiter-view", response_model=AuthzProbeResponse)
def recruiter_candidate_scope_probe(
    candidate_id: uuid.UUID,
    candidate: Candidate = Depends(RecruiterCandidateScopeDep),
    user: User = Depends(require_recruiter_role),
) -> AuthzProbeResponse:
    return AuthzProbeResponse(resource_type="candidate_scope", resource_id=candidate.id, role=user.role)
