"""DTOs for skill normalization. This is not candidate-job matching."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ResolutionType = Literal["canonical", "alias", "fuzzy", "unmatched"]
RelationEvidence = Literal["exact", "child", "parent", "related", "none"]


class SkillNormalizationResult(BaseModel):
    """Outcome of resolving one raw mention against an ontology version."""

    raw_text: str
    normalized_text: str
    canonical_skill_id: uuid.UUID | None = None
    canonical_skill_name: str | None = None
    resolution_type: ResolutionType
    ontology_version: str
    normalization_confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
    source_section: str | None = None
    evidence: str
    start: int | None = None
    end: int | None = None


class SkillRelationshipView(BaseModel):
    """Directed hierarchy/relatedness. Not a match score."""

    job_skill_id: uuid.UUID
    job_skill_name: str
    candidate_skill_id: uuid.UUID
    candidate_skill_name: str
    evidence_type: RelationEvidence
    hops: int | None = None
    ontology_version: str


class SkillCreate(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=128)


class AliasCreate(BaseModel):
    skill_id: uuid.UUID
    alias: str = Field(min_length=1, max_length=255)


class RelationCreate(BaseModel):
    source_skill_id: uuid.UUID
    target_skill_id: uuid.UUID
    relation: Literal["parent_of", "related_to", "similar_to"]
    weight: float = Field(default=1, ge=0, le=1)


class VersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64)
    activate: bool = False


class SkillView(BaseModel):
    id: uuid.UUID
    canonical_name: str
    slug: str
    description: str | None = None
    category: str | None = None
    status: str


class AliasView(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    alias: str
    normalized_alias: str


class RelationView(BaseModel):
    id: uuid.UUID
    source_skill_id: uuid.UUID
    target_skill_id: uuid.UUID
    relation: str
    weight: float


class OntologyVersionView(BaseModel):
    id: uuid.UUID
    version: str
    checksum: str
    status: str
    activated_at: datetime | None = None


class SkillListResponse(BaseModel):
    ontology_version: str | None
    items: list[SkillView]


class ValidationReport(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
