from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EmbeddingOwnerType, ScoringMode, enum_values

if TYPE_CHECKING:
    from app.models.candidates import Candidate
    from app.models.jobs import Job
    from app.models.ontology import OntologyVersion


class Embedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Encoder identity is stored per row. ANN indexes wait until dimension is chosen."""

    __tablename__ = "embeddings"
    __table_args__ = (
        CheckConstraint(f"owner_type IN {enum_values(EmbeddingOwnerType)}", name="owner_type"),
        CheckConstraint("dimensions > 0", name="dimensions"),
        UniqueConstraint(
            "owner_type",
            "owner_id",
            "chunk_type",
            "model_name",
            "model_version",
            "embedding_text_version",
            name="uq_embeddings_owner_model_text",
        ),
        Index("ix_embeddings_owner", "owner_type", "owner_id"),
    )

    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(64), nullable=False, default="full")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_text_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(), nullable=False)


class MatchRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_runs"
    __table_args__ = (
        CheckConstraint(f"scoring_mode IN {enum_values(ScoringMode)}", name="scoring_mode"),
        CheckConstraint(
            "scoring_mode <> 'trained' OR model_version IS NOT NULL",
            name="trained_requires_model_version",
        ),
        Index("ix_match_runs_candidate_job_created", "candidate_id", "job_id", "created_at"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    scoring_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(128))
    ontology_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ontology_versions.id", ondelete="RESTRICT")
    )
    feature_schema_version: Mapped[str | None] = mapped_column(String(64))
    weight_set_version: Mapped[str | None] = mapped_column(String(64))
    current_match: Mapped[float | None] = mapped_column(Numeric(5, 2))
    potential: Mapped[float | None] = mapped_column(Numeric(5, 2))
    semantic_similarity: Mapped[float | None] = mapped_column(Numeric(6, 5))
    project_relevance: Mapped[float | None] = mapped_column(Numeric(6, 5))
    experience_relevance: Mapped[float | None] = mapped_column(Numeric(6, 5))
    feature_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    unconfirmed_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    candidate: Mapped[Candidate] = relationship()
    job: Mapped[Job] = relationship()
    ontology_version: Mapped[OntologyVersion | None] = relationship()
    explanation: Mapped[MatchExplanation | None] = relationship(back_populates="match_run")
    features: Mapped[FeatureSnapshot | None] = relationship(back_populates="match_run")


class MatchExplanation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_explanations"

    match_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    traces: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    match_run: Mapped[MatchRun] = relationship(back_populates="explanation")


class FeatureSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Frozen inference features for later training. No metrics are stored here."""

    __tablename__ = "feature_snapshots"

    match_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    feature_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    match_run: Mapped[MatchRun] = relationship(back_populates="features")
