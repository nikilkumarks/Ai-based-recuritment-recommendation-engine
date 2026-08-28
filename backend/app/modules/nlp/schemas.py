"""DTOs for NLP drafts. Not SQLAlchemy models. Not match scores."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None = None
    source_section: str | None = None
    evidence: str | None = None
    start: int | None = None
    end: int | None = None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)


class SkillMention(BaseModel):
    """Raw skill mention. Not a canonical ontology skill."""

    raw_text: str
    normalized_text: str
    source_section: str | None = None
    evidence: str
    start: int | None = None
    end: int | None = None
    extraction_confidence: float = Field(default=0.85, ge=0, le=1)


class ContactDraft(BaseModel):
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ExperienceDraft(BaseModel):
    job_title: str | None = None
    employer: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    years_experience: float | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class EducationDraft(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    education_level: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ProjectDraft(BaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    technologies: list[SkillMention] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class CertificationDraft(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_url: str | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ProfileDraft(BaseModel):
    """Extraction result. Not a confirmed candidate profile. Not a match score."""

    summary: str | None = None
    contact: ContactDraft = Field(default_factory=ContactDraft)
    skills: list[SkillMention] = Field(default_factory=list)
    experience: list[ExperienceDraft] = Field(default_factory=list)
    education: list[EducationDraft] = Field(default_factory=list)
    projects: list[ProjectDraft] = Field(default_factory=list)
    certifications: list[CertificationDraft] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    nlp_pipeline_version: str
    parser_version: str | None = None
    warnings: list[str] = Field(default_factory=list)


class JobRequirementsDraft(BaseModel):
    """Extraction result for a job description. Skills are raw mentions, not ontology IDs."""

    title: str | None = None
    required_skills: list[SkillMention] = Field(default_factory=list)
    preferred_skills: list[SkillMention] = Field(default_factory=list)
    min_years_experience: float | None = None
    education_level: str | None = None
    seniority: str | None = None
    location: str | None = None
    employment_type: str | None = None
    other_requirements: list[str] = Field(default_factory=list)
    nlp_pipeline_version: str
    warnings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
