"""Versioned feature-schema-v1 extraction. Unknown stays unknown."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.modules.matching.constants import FEATURE_SCHEMA_VERSION
from app.modules.matching.evidence import SkillEvidence
from app.modules.matching.policies import ScoringPolicy


def build_feature_snapshot(
    *,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    ontology_version: str,
    policy: ScoringPolicy,
    required: list[SkillEvidence],
    preferred: list[SkillEvidence],
    embedding_meta: dict[str, Any],
    semantic: dict[str, Any],
    experience: dict[str, Any],
    education: dict[str, Any],
    projects: dict[str, Any],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    exact_required = [item for item in required if item.kind == "exact"]
    child_required = [item for item in required if item.kind == "child"]
    parent_required = [item for item in required if item.kind == "parent"]
    related_required = [item for item in required if item.kind == "related"]
    missing_required = [item for item in required if item.kind == "missing"]
    exact_preferred = [item for item in preferred if item.kind == "exact"]
    required_count = len(required)
    preferred_count = len(preferred)
    hops = [item.hops for item in required if item.kind != "exact" and item.kind != "missing" and item.hops]
    snapshot = {
        "feature_schema_version": policy.feature_schema_version or FEATURE_SCHEMA_VERSION,
        "candidate_id": str(candidate_id),
        "job_id": str(job_id),
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "ontology_version": ontology_version,
        "weight_set_version": policy.weight_set_version,
        "related_required_credit": policy.related_required_credit,
        "project_cosine_threshold": policy.project_cosine_threshold,
        "experience_cosine_threshold": policy.experience_cosine_threshold,
        "required_skill_count": required_count,
        "matched_required_skill_count": len(exact_required),
        "partial_required_skill_count": len(child_required),
        "related_required_skill_count": len(related_required),
        "missing_required_skill_count": len(missing_required),
        "parent_required_skill_count": len(parent_required),
        "preferred_skill_count": preferred_count,
        "matched_preferred_skill_count": len(exact_preferred),
        "required_skill_coverage": _coverage(len(exact_required), required_count),
        "preferred_skill_coverage": _coverage(len(exact_preferred), preferred_count),
        "exact_alias_matches": sum(1 for item in exact_required if item.via_alias),
        "parent_matches": len(parent_required),
        "child_matches": len(child_required),
        "related_matches": len(related_required),
        "average_gap_distance": _mean(hops),
        **embedding_meta,
        **semantic,
        **experience,
        **education,
        **projects,
    }
    return snapshot


def _coverage(matched: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return round(matched / total, 4)


def _mean(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)
