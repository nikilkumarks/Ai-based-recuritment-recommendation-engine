"""Deterministic gap list. Potential is not calculated here."""

from __future__ import annotations

from app.modules.matching.evidence import SkillEvidence


def required_gaps(required: list[SkillEvidence]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for item in required:
        if item.kind == "exact":
            continue
        gaps.append(
            {
                "skill": item.job_skill_name,
                "skill_id": str(item.job_skill_id),
                "type": item.kind,
            }
        )
    return gaps
