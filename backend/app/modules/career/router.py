"""Thin career-path HTTP API. Candidate-private suggested skill paths."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.career.schemas import CareerPathListResponse
from app.modules.career.service import CareerService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["career"])


def get_career_service(db: Session = Depends(get_db)) -> CareerService:
    return CareerService(db)


@router.get("/candidates/{candidate_id}/career-paths", response_model=CareerPathListResponse)
def list_career_paths(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = None,
    user: User = Depends(get_current_active_user),
    service: CareerService = Depends(get_career_service),
) -> CareerPathListResponse:
    """Suggested Skill Path. Not a guaranteed career path and not a hiring probability."""
    return service.list_paths(user=user, candidate_id=candidate_id, job_id=job_id)
