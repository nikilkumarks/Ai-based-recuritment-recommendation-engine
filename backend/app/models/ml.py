from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MlModelStatus, TrainingRunStatus, enum_values

if TYPE_CHECKING:
    from app.models.ontology import OntologyVersion


class DatasetSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_snapshots"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))


class MlModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ml_models"
    __table_args__ = (
        CheckConstraint(f"status IN {enum_values(MlModelStatus)}", name="status"),
        Index(
            "uq_ml_models_one_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    ontology_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ontology_versions.id", ondelete="RESTRICT")
    )
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    checksum: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MlModelStatus.CANDIDATE.value
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ontology_version: Mapped[OntologyVersion | None] = relationship()


class MlTrainingRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ml_training_runs"
    __table_args__ = (CheckConstraint(f"status IN {enum_values(TrainingRunStatus)}", name="status"),)

    dataset_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_snapshots.id", ondelete="RESTRICT")
    )
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    git_sha: Mapped[str | None] = mapped_column(String(40))
    feature_schema_version: Mapped[str | None] = mapped_column(String(64))
    ontology_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ontology_versions.id", ondelete="RESTRICT")
    )
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TrainingRunStatus.QUEUED.value
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dataset_snapshot: Mapped[DatasetSnapshot | None] = relationship()
    ontology_version: Mapped[OntologyVersion | None] = relationship()
