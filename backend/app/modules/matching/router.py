"""Thin matching HTTP API. Scoring lives in MatchingService."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.identity.dependencies import get_current_active_user
from app.modules.matching.schemas import (
    CandidateJobListResponse,
    CounterfactualRequest,
    CounterfactualResult,
    JobCandidateListResponse,
    MatchResult,
)
from app.modules.matching.service import MatchingService

router = APIRouter(tags=["matching"])


def get_matching_service(db: Session = Depends(get_db)) -> MatchingService:
    return MatchingService(db)


@router.get("/candidates/{candidate_id}/jobs", response_model=CandidateJobListResponse)
def list_candidate_jobs(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: MatchingService = Depends(get_matching_service),
) -> CandidateJobListResponse:
    """Baseline current_match per visible job. Not a trained ranker."""
    return service.list_jobs_for_candidate(user=user, candidate_id=candidate_id)


@router.get("/candidates/{candidate_id}/jobs/{job_id}/match", response_model=MatchResult)
def get_candidate_job_match(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: MatchingService = Depends(get_matching_service),
) -> MatchResult:
    return service.match_detail(user=user, candidate_id=candidate_id, job_id=job_id)


@router.post(
    "/candidates/{candidate_id}/jobs/{job_id}/counterfactual",
    response_model=CounterfactualResult,
)
def simulate_skill(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: CounterfactualRequest,
    user: User = Depends(get_current_active_user),
    service: MatchingService = Depends(get_matching_service),
) -> CounterfactualResult:
    """In-memory skill addition. Does not write candidate skills or persist a match run."""
    return service.simulate_add_skill(
        user=user,
        candidate_id=candidate_id,
        job_id=job_id,
        skill_id=payload.skill_id,
    )


@router.get("/jobs/{job_id}/candidates", response_model=JobCandidateListResponse)
def list_job_candidates(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: MatchingService = Depends(get_matching_service),
) -> JobCandidateListResponse:
    """Baseline current_match DESC. This is baseline sorting, not a trained ranker."""
    return service.list_candidates_for_job(user=user, job_id=job_id)
