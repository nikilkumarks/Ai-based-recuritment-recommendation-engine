"""Embedding HTTP routes. No ranking. Raw vectors are not returned."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.authorization.dependencies import require_admin_role
from app.modules.embeddings.schemas import EmbeddingStatus, SimilarityRequest, SimilarityResponse
from app.modules.embeddings.service import EmbeddingService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["embeddings"])


def get_embedding_service(db: Session = Depends(get_db)) -> EmbeddingService:
    return EmbeddingService(db)


@router.get("/candidates/{candidate_id}/profile/embedding", response_model=EmbeddingStatus)
def get_profile_embedding(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingStatus:
    return service.profile_status(user=user, candidate_id=candidate_id)


@router.post("/candidates/{candidate_id}/profile/embedding", response_model=EmbeddingStatus)
def embed_profile(
    candidate_id: uuid.UUID,
    force: bool = False,
    user: User = Depends(get_current_active_user),
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingStatus:
    return service.embed_candidate_profile(user=user, candidate_id=candidate_id, force=force)


@router.get("/jobs/{job_id}/embedding", response_model=EmbeddingStatus)
def get_job_embedding(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingStatus:
    return service.job_status(user=user, job_id=job_id)


@router.post("/jobs/{job_id}/embedding", response_model=EmbeddingStatus)
def embed_job(
    job_id: uuid.UUID,
    force: bool = False,
    user: User = Depends(get_current_active_user),
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingStatus:
    return service.embed_job(user=user, job_id=job_id, force=force)


@router.post("/admin/embeddings/similarity", response_model=SimilarityResponse)
def admin_similarity(
    payload: SimilarityRequest,
    user: User = Depends(require_admin_role),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SimilarityResponse:
    return service.similarity(user=user, payload=payload)
