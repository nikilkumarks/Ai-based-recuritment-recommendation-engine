from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConfirmationStatus, JobStatus, enum_values

if TYPE_CHECKING:
    from app.models.identity import Organization, User
    from app.models.ontology import Skill


class Job(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(f"status IN {enum_values(JobStatus)}", name="status"),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="salary_range",
        ),
        Index("ix_jobs_organization_status", "organization_id", "status"),
        Index("ix_jobs_organization_created_at", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    seniority: Mapped[str | None] = mapped_column(String(64))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.DRAFT.value)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(back_populates="jobs")
    creator: Mapped[User | None] = relationship()
    requirements: Mapped[list[JobRequirement]] = relationship(back_populates="job")


class JobRequirement(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "job_requirements"
    __table_args__ = (
        CheckConstraint(
            f"confirmation_status IN {enum_values(ConfirmationStatus)}",
            name="confirmation_status",
        ),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    min_years_experience: Mapped[float | None] = mapped_column(Numeric(5, 2))
    education_level: Mapped[str | None] = mapped_column(String(64))
    confirmation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ConfirmationStatus.DRAFT.value
    )
    parser_version: Mapped[str | None] = mapped_column(String(64))
    extracted_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    job: Mapped[Job] = relationship(back_populates="requirements")
    required_skills: Mapped[list[JobRequiredSkill]] = relationship(back_populates="requirement")
    preferred_skills: Mapped[list[JobPreferredSkill]] = relationship(back_populates="requirement")


class JobRequiredSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_required_skills"
    __table_args__ = (
        UniqueConstraint(
            "job_requirement_id", "skill_id", name="uq_job_required_skills_req_skill"
        ),
    )

    job_requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    importance: Mapped[str] = mapped_column(String(32), nullable=False, default="high")

    requirement: Mapped[JobRequirement] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship()


class JobPreferredSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_preferred_skills"
    __table_args__ = (
        UniqueConstraint(
            "job_requirement_id", "skill_id", name="uq_job_preferred_skills_req_skill"
        ),
    )

    job_requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    importance: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")

    requirement: Mapped[JobRequirement] = relationship(back_populates="preferred_skills")
    skill: Mapped[Skill] = relationship()
