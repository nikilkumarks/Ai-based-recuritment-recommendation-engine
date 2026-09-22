"""Thin recruiter-decision HTTP API. Append-only; does not train models."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.applications.schemas import (
    RecruiterDecisionCreate,
    RecruiterDecisionListResponse,
    RecruiterDecisionView,
)
from app.modules.applications.service import ApplicationsService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["decisions"])


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
