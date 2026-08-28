"""HTTP routes for candidate profile draft, edit, and confirmation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.candidates.schemas import ProfileResponse, ProfileUpdate, ProfileView
from app.modules.candidates.service import CandidateService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["profiles"])


def get_candidate_service(db: Session = Depends(get_db)) -> CandidateService:
    return CandidateService(db)


@router.get("/candidates/{candidate_id}/profile", response_model=ProfileResponse)
def get_profile(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: CandidateService = Depends(get_candidate_service),
) -> ProfileResponse:
    return service.get_profile(user=user, candidate_id=candidate_id)


@router.put("/candidates/{candidate_id}/profile", response_model=ProfileView)
def update_profile(
    candidate_id: uuid.UUID,
    payload: ProfileUpdate,
    user: User = Depends(get_current_active_user),
    service: CandidateService = Depends(get_candidate_service),
) -> ProfileView:
    return service.update_draft(user=user, candidate_id=candidate_id, payload=payload)


@router.post("/candidates/{candidate_id}/profile/confirm", response_model=ProfileView)
def confirm_profile(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: CandidateService = Depends(get_candidate_service),
) -> ProfileView:
    return service.confirm(user=user, candidate_id=candidate_id)


@router.post("/candidates/{candidate_id}/resumes/{resume_id}/extract", response_model=ProfileView)
def extract_resume_nlp(
    candidate_id: uuid.UUID,
    resume_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: CandidateService = Depends(get_candidate_service),
) -> ProfileView:
    return service.rerun_resume_nlp(user=user, candidate_id=candidate_id, resume_id=resume_id)
