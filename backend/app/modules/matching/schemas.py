"""Match result DTOs. Not SQLAlchemy models. Score range is 0.0–1.0 only."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ScoringModeLiteral = Literal["baseline", "trained"]


class SkillMatchItem(BaseModel):
    skill_id: uuid.UUID
    skill: str
    evidence_type: str
    candidate_skill_id: uuid.UUID | None = None
    candidate_evidence: str | None = None
    hops: int | None = None


class GapItem(BaseModel):
    skill: str
    skill_id: uuid.UUID
    type: str


class ScoreComponent(BaseModel):
    name: str
    value: float
    weight: float
    available: bool


class MatchResult(BaseModel):
    """Public match contract. Potential is heuristic closability, not hiring probability.

    model_relevance_score is a shortlist-prediction score, not a hire probability.
    """

    candidate_id: uuid.UUID
    job_id: uuid.UUID
    current_match: float = Field(ge=0.0, le=1.0)
    potential: float | None = Field(default=None, ge=0.0, le=1.0)
    potential_status: Literal["available", "not_applicable"] = "not_applicable"
    potential_components: dict[str, float | None] = Field(default_factory=dict)
    suggested_skill_paths: list[dict[str, Any]] = Field(default_factory=list)
    semantic_similarity: float | None = None
    semantic_similarity_available: bool
    scoring_mode: ScoringModeLiteral = "baseline"
    model_version: str | None = None
    model_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    ml_explanations: list[dict[str, Any]] = Field(default_factory=list)
    fallback_reason: str | None = None
    feature_schema_version: str
    ontology_version: str
    weight_set_version: str
    required_skill_coverage: float
    preferred_skill_coverage: float
    matched_skills: list[SkillMatchItem] = Field(default_factory=list)
    partial_skills: list[SkillMatchItem] = Field(default_factory=list)
    related_skills: list[SkillMatchItem] = Field(default_factory=list)
    missing_skills: list[SkillMatchItem] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    explanations: list[dict[str, Any]] = Field(default_factory=list)
    components: list[ScoreComponent] = Field(default_factory=list)
    match_run_id: uuid.UUID | None = None
    created_at: datetime | None = None


class CandidateJobMatchSummary(BaseModel):
    job_id: uuid.UUID
    job_title: str
    current_match: float = Field(ge=0.0, le=1.0)
    potential: float | None = Field(default=None, ge=0.0, le=1.0)
    potential_status: Literal["available", "not_applicable"] = "not_applicable"
    required_skill_coverage: float
    missing_skills: list[SkillMatchItem] = Field(default_factory=list)
    partial_skills: list[SkillMatchItem] = Field(default_factory=list)
    related_skills: list[SkillMatchItem] = Field(default_factory=list)
    scoring_mode: ScoringModeLiteral = "baseline"
    model_version: str | None = None
    model_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_similarity_available: bool
    sort_note: str = "baseline_current_match_desc"


class CandidateJobListResponse(BaseModel):
    items: list[CandidateJobMatchSummary]
    scoring_mode: ScoringModeLiteral = "baseline"
    sort: str = "current_match DESC (baseline sorting, not a trained ranker)"


class JobCandidateMatchSummary(BaseModel):
    candidate_id: uuid.UUID
    identifier: str
    headline: str | None = None
    current_match: float = Field(ge=0.0, le=1.0)
    potential: float | None = Field(default=None, ge=0.0, le=1.0)
    potential_status: Literal["available", "not_applicable"] = "not_applicable"
    required_skill_coverage: float
    missing_skills: list[SkillMatchItem] = Field(default_factory=list)
    related_skills: list[SkillMatchItem] = Field(default_factory=list)
    scoring_mode: ScoringModeLiteral = "baseline"
    model_version: str | None = None
    model_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    current_decision: str | None = None
    is_applicant: bool = False
    application_status: str | None = None
    sort_note: str = "baseline_current_match_desc"



class JobCandidateListResponse(BaseModel):
    job_id: uuid.UUID
    items: list[JobCandidateMatchSummary]
    scoring_mode: ScoringModeLiteral = "baseline"
    sort: str = "current_match DESC (baseline sorting, not a trained ranker)"


class CounterfactualRequest(BaseModel):
    skill_id: uuid.UUID


class CounterfactualResult(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    skill_id: uuid.UUID
    skill_name: str
    baseline_current_match: float
    simulated_current_match: float
    delta: float
    potential_before: float | None = None
    potential_after: float | None = None
    potential_delta: float | None = None
    persisted: bool = False
    affected_evidence: list[dict[str, Any]] = Field(default_factory=list)
    affected_gaps: list[dict[str, Any]] = Field(default_factory=list)
    scoring_mode: ScoringModeLiteral = "baseline"
    model_version: str | None = None
