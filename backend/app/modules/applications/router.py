"""Thin recruiter-decision HTTP API. Append-only; does not train models."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationView,
    CandidateDecisionCreate,
    CandidateDecisionView,
    RecruiterDecisionCreate,
    RecruiterDecisionListResponse,
    RecruiterDecisionView,
)
from app.modules.applications.service import ApplicationsService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["applications", "decisions"])


def get_applications_service(db: Session = Depends(get_db)) -> ApplicationsService:
    return ApplicationsService(db)


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/decisions",
    response_model=RecruiterDecisionView,
    status_code=201,
)
def create_decision(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    payload: RecruiterDecisionCreate,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> RecruiterDecisionView:
    """Append a recruiter decision. Does not overwrite history and does not train a model."""
    return service.create_decision(
        user=user, job_id=job_id, candidate_id=candidate_id, payload=payload
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/decisions",
    response_model=RecruiterDecisionListResponse,
)
def list_decisions(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> RecruiterDecisionListResponse:
    return service.list_decisions(user=user, job_id=job_id, candidate_id=candidate_id)


@router.post(
    "/candidates/{candidate_id}/applications",
    response_model=ApplicationView,
    status_code=201,
)
def create_application(
    candidate_id: uuid.UUID,
    payload: ApplicationCreate | None = None,
    job_id: uuid.UUID | None = None,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> ApplicationView:
    """Candidate applies to a job."""
    target_job_id = payload.job_id if payload is not None else job_id
    if target_job_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="job_id is required in JSON body or query parameter")
    return service.create_application(user=user, candidate_id=candidate_id, job_id=target_job_id)


@router.get(
    "/candidates/{candidate_id}/applications",
    response_model=ApplicationListResponse,
)
def list_candidate_applications(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> ApplicationListResponse:
    """List candidate's application history."""
    return service.list_candidate_applications(user=user, candidate_id=candidate_id)


@router.get(
    "/candidates/{candidate_id}/jobs/{job_id}/application",
    response_model=ApplicationView | None,
)
def get_candidate_application(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> ApplicationView | None:
    """Get application status for candidate/job pair."""
    return service.get_candidate_application(user=user, candidate_id=candidate_id, job_id=job_id)


@router.post(
    "/candidates/{candidate_id}/jobs/{job_id}/decisions",
    response_model=CandidateDecisionView,
    status_code=201,
)
def create_candidate_decision(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: CandidateDecisionCreate,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> CandidateDecisionView:
    """Record candidate action (save / dismiss)."""
    return service.create_candidate_decision(
        user=user, candidate_id=candidate_id, job_id=job_id, action=payload.action
    )


@router.get(
    "/candidates/{candidate_id}/saved-jobs",
    response_model=list[uuid.UUID],
)
def list_saved_jobs(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: ApplicationsService = Depends(get_applications_service),
) -> list[uuid.UUID]:
    """List IDs of candidate's saved jobs."""
    return service.list_saved_jobs(user=user, candidate_id=candidate_id)

