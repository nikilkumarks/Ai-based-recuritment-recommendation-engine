"""Deterministic baseline composer. Interpretable reference, not a trained model."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.matching.constants import SCORE_DECIMALS, SCORE_MAX, SCORE_MIN
from app.modules.matching.policies import ScoringPolicy


@dataclass(frozen=True)
class ComponentScore:
    name: str
    value: float
    weight: float
    available: bool


@dataclass(frozen=True)
class ComposerResult:
    current_match: float
    components: tuple[ComponentScore, ...]
    used_weight_sum: float

    def as_dict(self) -> dict[str, object]:
        return {
            "current_match": self.current_match,
            "used_weight_sum": self.used_weight_sum,
            "components": [
                {
                    "name": item.name,
                    "value": item.value,
                    "weight": item.weight,
                    "available": item.available,
                }
                for item in self.components
            ],
        }


def clamp_score(value: float) -> float:
    if value < SCORE_MIN:
        return SCORE_MIN
    if value > SCORE_MAX:
        return SCORE_MAX
    return round(value, SCORE_DECIMALS)


def compose(features: dict[str, object], policy: ScoringPolicy) -> ComposerResult:
    """Reconstruct current_match from a feature vector and scoring policy."""
    required_value = _required_coverage(features)
    preferred_value = _preferred_coverage(features)
    semantic_available = bool(features.get("semantic_similarity_available"))
    semantic_raw = features.get("profile_job_cosine")
    semantic_value = 0.0
    if semantic_available and isinstance(semantic_raw, (int, float)):
        semantic_value = max(0.0, min(1.0, float(semantic_raw)))
    experience_value = _experience_component(features)
    education_project_value = _education_project_component(features)

    parts = [
        ComponentScore("required", required_value, policy.required, True),
        ComponentScore("preferred", preferred_value, policy.preferred, True),
        ComponentScore("semantic", semantic_value, policy.semantic, semantic_available),
        ComponentScore("experience", experience_value, policy.experience, True),
        ComponentScore(
            "education_project",
            education_project_value,
            policy.education_project,
            True,
        ),
    ]
    used = [item for item in parts if item.available and item.weight > 0]
    weight_sum = sum(item.weight for item in used)
    if weight_sum <= 0:
        score = 0.0
    else:
        score = sum(item.value * item.weight for item in used) / weight_sum
    return ComposerResult(
        current_match=clamp_score(score),
        components=tuple(parts),
        used_weight_sum=round(weight_sum, SCORE_DECIMALS),
    )


def _ratio(matched: object, total: object) -> float:
    count = int(total or 0)
    if count <= 0:
        return 1.0
    return clamp_score(int(matched or 0) / count)


def _required_coverage(features: dict[str, object]) -> float:
    return _ratio(features.get("matched_required_skill_count"), features.get("required_skill_count"))


def _preferred_coverage(features: dict[str, object]) -> float:
    return _ratio(features.get("matched_preferred_skill_count"), features.get("preferred_skill_count"))


def _experience_component(features: dict[str, object]) -> float:
    required = features.get("required_experience_years")
    got = features.get("candidate_experience_years")
    if required is None:
        return 1.0
    required_years = float(required)
    if required_years <= 0:
        return 1.0
    if got is None:
        # Unknown years are not treated as failure.
        return 1.0
    got_years = float(got)
    if got_years >= required_years:
        return 1.0
    return clamp_score(got_years / required_years)


def _education_project_component(features: dict[str, object]) -> float:
    education = _education_component(features)
    project = _project_component(features)
    return clamp_score((education + project) / 2.0)


def _education_component(features: dict[str, object]) -> float:
    if not features.get("education_requirement_present"):
        return 1.0
    alignment = features.get("education_alignment")
    if alignment is None:
        # Unknown candidate education is not a failure when a requirement exists.
        return 1.0
    return 1.0 if alignment else 0.0


def _project_component(features: dict[str, object]) -> float:
    has_projects = int(features.get("candidate_project_count") or 0) > 0
    if not features.get("project_evidence_present") and not has_projects:
        return 1.0
    return 1.0 if int(features.get("relevant_project_count") or 0) > 0 else 0.0
