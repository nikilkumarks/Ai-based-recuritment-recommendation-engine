"""Embedding DTOs. Never include raw vectors for candidate/recruiter responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EmbeddingStatusName = Literal["missing", "current", "stale", "incompatible"]


class EncoderMeta(BaseModel):
    model_name: str
    model_version: str
    dimensions: int
    embedding_text_version: str


class EmbeddingStatus(BaseModel):
    """Safe metadata only. Cosine similarity is not a recruitment score."""

    status: EmbeddingStatusName
    owner_type: str
    owner_id: uuid.UUID
    chunk_type: str = "full"
    model_name: str | None = None
    model_version: str | None = None
    dimensions: int | None = None
    embedding_text_version: str | None = None
    content_hash: str | None = None
    created_at: datetime | None = None
    reused: bool = False
    processing_job_id: uuid.UUID | None = None


class EmbeddingRunRequest(BaseModel):
    force: bool = False


class SimilarityRequest(BaseModel):
    left_embedding_id: uuid.UUID | None = None
    right_embedding_id: uuid.UUID | None = None
    left_owner_type: str | None = None
    left_owner_id: uuid.UUID | None = None
    right_owner_type: str | None = None
    right_owner_id: uuid.UUID | None = None
    left_chunk_type: str = "full"
    right_chunk_type: str = "full"


class SimilarityResponse(BaseModel):
    """Semantic feature only. Not a match percentage and not a ranking."""

    similarity: float = Field(ge=-1, le=1)
    model_name: str
    model_version: str
    dimensions: int
    embedding_text_version: str
