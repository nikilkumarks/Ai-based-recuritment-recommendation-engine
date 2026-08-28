from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
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
from app.models.enums import ConfirmationStatus, ParseStatus, SkillAttributionSource, enum_values

if TYPE_CHECKING:
    from app.models.identity import User
    from app.models.ontology import Skill


class Candidate(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    user: Mapped[User] = relationship(back_populates="candidate")
    resumes: Mapped[list[Resume]] = relationship(back_populates="candidate")
    profiles: Mapped[list[CandidateProfile]] = relationship(back_populates="candidate")


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Blob metadata only. File bytes live in object storage under storage_key."""

    __tablename__ = "resumes"
    __table_args__ = (CheckConstraint(f"parse_status IN {enum_values(ParseStatus)}", name="parse_status"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parse_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ParseStatus.QUEUED.value
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidate: Mapped[Candidate] = relationship(back_populates="resumes")
    extraction_revisions: Mapped[list[ExtractionRevision]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExtractionRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Raw parser output. Confirmed profiles are stored separately and are not overwritten."""

    __tablename__ = "extraction_revisions"
    __table_args__ = (
        UniqueConstraint("resume_id", "revision_number", name="uq_extraction_revisions_resume_rev"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    resume: Mapped[Resume] = relationship(back_populates="extraction_revisions")


class CandidateProfile(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    """Source of truth for matching after confirmation. Re-parse must not overwrite this."""

    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint(
            f"confirmation_status IN {enum_values(ConfirmationStatus)}",
            name="confirmation_status",
        ),
        UniqueConstraint("candidate_id", "profile_version", name="uq_candidate_profiles_version"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("extraction_revisions.id", ondelete="SET NULL")
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    summary: Mapped[str | None] = mapped_column(Text)
    confirmation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ConfirmationStatus.DRAFT.value
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    candidate: Mapped[Candidate] = relationship(back_populates="profiles")
    source_revision: Mapped[ExtractionRevision | None] = relationship()
    experience_items: Mapped[list[ExperienceItem]] = relationship(back_populates="profile")
    education_items: Mapped[list[EducationItem]] = relationship(back_populates="profile")
    project_items: Mapped[list[ProjectItem]] = relationship(back_populates="profile")
    certification_items: Mapped[list[CertificationItem]] = relationship(back_populates="profile")
    skills: Mapped[list[CandidateSkill]] = relationship(back_populates="profile")


class ExperienceItem(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "experience_items"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    employer: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    years_experience: Mapped[float | None] = mapped_column(Numeric(5, 2))
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    profile: Mapped[CandidateProfile] = relationship(back_populates="experience_items")


class EducationItem(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "education_items"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    education_level: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[CandidateProfile] = relationship(back_populates="education_items")


class ProjectItem(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "project_items"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    profile: Mapped[CandidateProfile] = relationship(back_populates="project_items")


class CertificationItem(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "certification_items"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(255))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    credential_url: Mapped[str | None] = mapped_column(String(2048))

    profile: Mapped[CandidateProfile] = relationship(back_populates="certification_items")


class CandidateSkill(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id", "skill_id", name="uq_candidate_skills_profile_skill"
        ),
        CheckConstraint(
            f"source IN {enum_values(SkillAttributionSource)}",
            name="source",
        ),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence"),
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    proficiency_level: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SkillAttributionSource.CANDIDATE.value
    )
    evidence_span: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    profile: Mapped[CandidateProfile] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()
