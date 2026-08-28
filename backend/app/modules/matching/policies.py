"""Configurable baseline scoring policy. Heuristic until labeled validation exists."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.modules.matching.constants import (
    DEFAULT_EXPERIENCE_COSINE_THRESHOLD,
    DEFAULT_PROJECT_COSINE_THRESHOLD,
    DEFAULT_WEIGHT_EDUCATION_PROJECT,
    DEFAULT_WEIGHT_EXPERIENCE,
    DEFAULT_WEIGHT_PREFERRED,
    DEFAULT_WEIGHT_REQUIRED,
    DEFAULT_WEIGHT_SEMANTIC,
    FEATURE_SCHEMA_VERSION,
    RELATED_REQUIRED_CREDIT,
    WEIGHT_SET_VERSION,
)


@dataclass(frozen=True)
class ScoringPolicy:
    """Deterministic weighted composer. Weights are starting heuristics, not empirically optimal."""

    weight_set_version: str
    feature_schema_version: str
    required: float
    preferred: float
    semantic: float
    experience: float
    education_project: float
    related_required_credit: float
    project_cosine_threshold: float
    experience_cosine_threshold: float

    def component_weights(self) -> dict[str, float]:
        return {
            "required": self.required,
            "preferred": self.preferred,
            "semantic": self.semantic,
            "experience": self.experience,
            "education_project": self.education_project,
        }


def scoring_policy() -> ScoringPolicy:
    settings = get_settings()
    return ScoringPolicy(
        weight_set_version=settings.match_weight_set_version or WEIGHT_SET_VERSION,
        feature_schema_version=settings.feature_schema_version or FEATURE_SCHEMA_VERSION,
        required=settings.match_weight_required,
        preferred=settings.match_weight_preferred,
        semantic=settings.match_weight_semantic,
        experience=settings.match_weight_experience,
        education_project=settings.match_weight_education_project,
        related_required_credit=RELATED_REQUIRED_CREDIT,
        project_cosine_threshold=settings.project_evidence_cosine_threshold,
        experience_cosine_threshold=settings.experience_evidence_cosine_threshold,
    )


def default_scoring_policy() -> ScoringPolicy:
    return ScoringPolicy(
        weight_set_version=WEIGHT_SET_VERSION,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        required=DEFAULT_WEIGHT_REQUIRED,
        preferred=DEFAULT_WEIGHT_PREFERRED,
        semantic=DEFAULT_WEIGHT_SEMANTIC,
        experience=DEFAULT_WEIGHT_EXPERIENCE,
        education_project=DEFAULT_WEIGHT_EDUCATION_PROJECT,
        related_required_credit=RELATED_REQUIRED_CREDIT,
        project_cosine_threshold=DEFAULT_PROJECT_COSINE_THRESHOLD,
        experience_cosine_threshold=DEFAULT_EXPERIENCE_COSINE_THRESHOLD,
    )
