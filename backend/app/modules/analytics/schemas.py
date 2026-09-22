"""Analytics DTOs. Descriptive counts only; not model accuracy."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CountItem(BaseModel):
    name: str
    count: int


class DistributionBucket(BaseModel):
    bucket: str
    count: int


class RecruiterOverview(BaseModel):
    jobs: int
    candidates: int
    applications: int
    shortlist_count: int
    reject_count: int
    review_count: int
    decision_rate: float | None = None
    shortlist_rate: float | None = None
    disclaimer: str = (
        "Shortlist rate is not a hiring success rate. "
        "Recruiter decisions are behavioral labels, not ground-truth hiring outcomes."
    )


class SkillGapItem(BaseModel):
    skill: str
    required_jobs: int
    candidate_supply: int
    missing_comparisons: int = 0
    related_comparisons: int = 0


class RecruiterSkillsAnalytics(BaseModel):
    required_demand: list[CountItem]
    preferred_demand: list[CountItem]
    candidate_supply: list[CountItem]
    top_missing_skills: list[CountItem]
    top_adjacent_skills: list[CountItem]
    gaps: list[SkillGapItem] = Field(default_factory=list)


class RecruiterMatchingAnalytics(BaseModel):
    current_match: list[DistributionBucket]
    potential: list[DistributionBucket]
    required_skill_coverage: list[DistributionBucket]
    semantic_similarity: list[DistributionBucket]


class FunnelAnalytics(BaseModel):
    jobs: int
    applications: int
    reviewed: int
    shortlisted: int
    rejected: int


class DatasetSnapshotSummary(BaseModel):
    id: str
    name: str
    created_at: str | None = None
    row_count: int | None = None
    positive_count: int = 0
    negative_count: int = 0
    excluded_count: int = 0
    label_policy_version: str | None = None
    feature_schema_versions: list[str] = Field(default_factory=list)
    ontology_versions: list[str] = Field(default_factory=list)
    embedding_versions: list[str] = Field(default_factory=list)
    sufficient_for_training_experiment: bool = False
    trained: bool = False


class DatasetSnapshotDetail(DatasetSnapshotSummary):
    description: str | None = None
    checksum: str | None = None
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    source_decision_range: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    note: str = (
        "No trained model is produced until sufficient real labeled data exists. "
        "Recruiter shortlist/reject decisions are behavioral labels and are not "
        "ground-truth hiring outcomes."
    )


class MlModelSummary(BaseModel):
    id: str
    version: str
    algorithm: str
    status: str
    feature_schema_version: str
    dataset_snapshot_id: str | None = None
    created_at: str | None = None
    activated_at: str | None = None
    evaluation: dict[str, Any] | None = None
    baseline_comparison: dict[str, Any] = Field(default_factory=dict)
    activation: dict[str, Any] = Field(default_factory=dict)
    class_balance: dict[str, Any] | None = None
    leakage_checks: list[str] | None = None
    cv_folds: int | None = None
    random_seed: int | None = None
    test_fixture_only: bool = False
    warning: str | None = None
    target_note: str
