"""Versioned ML feature list for shortlist prediction. Not hiring features."""

from __future__ import annotations

import math
from typing import Any

ML_FEATURE_SCHEMA_VERSION = "ml-feature-schema-v1"
ML_PREPROCESS_VERSION = "ml-preprocess-v1"
SUPPORTED_SNAPSHOT_SCHEMAS = ("feature-schema-v1", "feature-schema-v2")

# Predictive columns in persist order. job_id/candidate_id are never included.
FEATURE_NAMES: tuple[str, ...] = (
    "required_skill_coverage",
    "preferred_skill_coverage",
    "required_skill_count",
    "matched_required_skill_count",
    "missing_required_skill_count",
    "related_required_skill_count",
    "partial_required_skill_count",
    "parent_required_skill_count",
    "preferred_skill_count",
    "matched_preferred_skill_count",
    "exact_alias_matches",
    "parent_matches",
    "child_matches",
    "related_matches",
    "average_gap_distance",
    "semantic_similarity_available",
    "profile_job_cosine",
    "current_match",
    "candidate_experience_years",
    "required_experience_years",
    "experience_satisfied",
    "experience_evidence_present",
    "education_requirement_present",
    "education_alignment",
    "candidate_project_count",
    "relevant_project_count",
    "project_evidence_present",
    "relevant_project_cosine",
    "potential",
    "potential_available",
    "potential_graph_closability",
    "potential_adjacent_skill_ratio",
    "potential_project_evidence",
    "potential_experience_evidence",
    "potential_certification_evidence",
    "potential_semantic_evidence",
)

NULLABLE_FEATURES: tuple[str, ...] = (
    "average_gap_distance",
    "profile_job_cosine",
    "candidate_experience_years",
    "required_experience_years",
    "experience_satisfied",
    "education_alignment",
    "relevant_project_cosine",
    "potential",
    "potential_graph_closability",
    "potential_adjacent_skill_ratio",
    "potential_project_evidence",
    "potential_experience_evidence",
    "potential_certification_evidence",
    "potential_semantic_evidence",
)

REQUIRED_FEATURES: tuple[str, ...] = (
    "required_skill_coverage",
    "current_match",
)

FORBIDDEN_FEATURE_KEYS = {
    "label",
    "decision",
    "action",
    "shortlist",
    "reject",
    "review",
    "hire",
    "reason",
    "recruiter_reason",
    "note",
    "decision_note",
    "recruiter_id",
    "decision_id",
    "decision_time",
    "candidate_id",
    "job_id",
    "organization_id",
    "name",
    "address",
    "gender",
    "religion",
    "caste",
    "race",
    "ethnicity",
    "disability",
    "age",
    "marital_status",
    "college_prestige",
    "college",
    "resume_text",
    "jd_text",
    "raw_text",
}

MISSING_FILL = 0.0
YEARS_MISSING_FILL = -1.0


def missing_flag_name(name: str) -> str:
    return f"{name}__missing"


def ordered_feature_names() -> list[str]:
    names: list[str] = []
    nullable = set(NULLABLE_FEATURES)
    for name in FEATURE_NAMES:
        names.append(name)
        if name in nullable:
            names.append(missing_flag_name(name))
    return names


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def vectorize_features(raw: dict[str, Any]) -> tuple[list[float], str | None]:
    """Deterministic missing-value policy. Same function is used at train and serve time."""
    values: list[float] = []
    nullable = set(NULLABLE_FEATURES)
    years = {"candidate_experience_years", "required_experience_years"}
    for name in FEATURE_NAMES:
        if name == "potential_available":
            status = str(raw.get("potential_status") or "")
            potential = raw.get("potential")
            present = potential is not None and status != "not_applicable"
            values.append(1.0 if present else 0.0)
            continue
        if name == "semantic_similarity_available":
            values.append(1.0 if raw.get("semantic_similarity_available") else 0.0)
            continue
        parsed = _as_float(raw.get(name))
        if name in REQUIRED_FEATURES and parsed is None:
            return [], f"missing_required_feature:{name}"
        if parsed is not None and not math.isfinite(parsed):
            return [], f"invalid_feature_value:{name}"
        if name in nullable:
            missing = parsed is None
            fill = YEARS_MISSING_FILL if name in years else MISSING_FILL
            values.append(fill if missing else parsed)
            values.append(1.0 if missing else 0.0)
        else:
            if parsed is None:
                values.append(MISSING_FILL)
            else:
                values.append(parsed)
    return values, None
