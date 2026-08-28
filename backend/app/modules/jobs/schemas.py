"""Job DTOs for description NLP and requirement confirmation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.nlp.schemas import JobRequirementsDraft
from app.modules.ontology.schemas import SkillNormalizationResult


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description_raw: str = Field(min_length=20, max_length=20000)
    organization_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=64)
    seniority: str | None = Field(default=None, max_length=64)


class JobSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    organization_id: uuid.UUID
    created_at: datetime


class JobRequirementView(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    confirmation_status: str
    parser_version: str | None = None
    min_years_experience: float | None = None
    education_level: str | None = None
    ontology_version: str | None = None
    draft: JobRequirementsDraft | None = None
    normalized_required_skills: list[SkillNormalizationResult] = Field(default_factory=list)
    normalized_preferred_skills: list[SkillNormalizationResult] = Field(default_factory=list)


class JobDetail(BaseModel):
    id: uuid.UUID
    title: str
    description_raw: str
    status: str
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    organization_id: uuid.UUID
    requirements: JobRequirementView | None = None


class JobRequirementUpdate(BaseModel):
    title: str | None = None
    required_skills: list[dict] | None = None
    preferred_skills: list[dict] | None = None
    min_years_experience: float | None = None
    education_level: str | None = None
    seniority: str | None = None
    location: str | None = None
    employment_type: str | None = None


class JobListResponse(BaseModel):
    items: list[JobSummary]
