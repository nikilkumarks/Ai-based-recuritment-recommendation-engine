"""Candidate profile DTOs for draft review and confirmation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.nlp.schemas import ProfileDraft
from app.modules.ontology.schemas import SkillNormalizationResult


class ManualSkillAddRequest(BaseModel):
    skill: str | None = None
    skill_identifier: str | None = None

    @property
    def skill_text(self) -> str:
        return (self.skill or self.skill_identifier or "").strip()


class ProfileUpdate(BaseModel):
    """Candidate edits to a draft. Skills remain raw mentions."""

    summary: str | None = None
    skills: list[dict] | None = None
    experience: list[dict] | None = None
    education: list[dict] | None = None
    projects: list[dict] | None = None
    certifications: list[dict] | None = None
    contact: dict | None = None



class ProfileView(BaseModel):
    id: uuid.UUID
    profile_version: int
    confirmation_status: str
    summary: str | None = None
    confirmed_at: datetime | None = None
    source_revision_id: uuid.UUID | None = None
    nlp_pipeline_version: str | None = None
    ontology_version: str | None = None
    draft: ProfileDraft | None = None
    normalized_skills: list[SkillNormalizationResult] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    certifications: list[dict] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    confirmed: ProfileView | None = None
    draft: ProfileView | None = None


class MessageResponse(BaseModel):
    message: str
