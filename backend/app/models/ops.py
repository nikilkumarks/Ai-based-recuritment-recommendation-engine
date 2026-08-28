from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProcessingJobStatus, ProcessingJobType, enum_values

if TYPE_CHECKING:
    from app.models.identity import User


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(f"type IN {enum_values(ProcessingJobType)}", name="type"),
        CheckConstraint(f"status IN {enum_values(ProcessingJobStatus)}", name="status"),
        Index("ix_processing_jobs_status", "status"),
    )

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProcessingJobStatus.QUEUED.value
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    error: Mapped[str | None] = mapped_column(String(4000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Do not persist resume text, passwords, tokens, or extra PII in metadata."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_resource", "resource_type", "resource_id"),)

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column()
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    actor: Mapped[User | None] = relationship()
