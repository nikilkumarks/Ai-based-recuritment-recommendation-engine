from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ApplicationStatus,
    CandidateDecisionAction,
    RecruiterDecisionAction,
    enum_values,
)

if TYPE_CHECKING:
    from app.models.candidates import Candidate
    from app.models.identity import User
    from app.models.jobs import Job


class Application(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_applications_candidate_job"),
        CheckConstraint(f"status IN {enum_values(ApplicationStatus)}", name="status"),
        Index("ix_applications_job_id", "job_id"),
        Index("ix_applications_candidate_id", "candidate_id"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ApplicationStatus.APPLIED.value
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    candidate: Mapped[Candidate] = relationship()
    job: Mapped[Job] = relationship()


class CandidateDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_decisions"
    __table_args__ = (
        CheckConstraint(f"action IN {enum_values(CandidateDecisionAction)}", name="action"),
        Index("ix_candidate_decisions_candidate_job_created", "candidate_id", "job_id", "created_at"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)

    candidate: Mapped[Candidate] = relationship()
    job: Mapped[Job] = relationship()


class RecruiterDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Potential future training labels. No action is assumed positive or negative here."""

    __tablename__ = "recruiter_decisions"
    __table_args__ = (
        CheckConstraint(f"action IN {enum_values(RecruiterDecisionAction)}", name="action"),
        Index("ix_recruiter_decisions_job_created", "job_id", "created_at"),
    )

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    recruiter: Mapped[User] = relationship()
    job: Mapped[Job] = relationship()
    candidate: Mapped[Candidate] = relationship()
