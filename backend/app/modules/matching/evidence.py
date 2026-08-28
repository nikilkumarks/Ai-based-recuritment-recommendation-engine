"""Ontology skill evidence. Exact/alias vs child/parent/related vs missing.

Does not infer hierarchy from embeddings. Related/child/parent are never exact.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.policies import classify_relationship

EvidenceKind = Literal["exact", "child", "parent", "related", "missing"]

_RANK: dict[str, int] = {"exact": 0, "child": 1, "parent": 2, "related": 3, "missing": 4}


@dataclass(frozen=True)
class SkillRef:
    skill_id: uuid.UUID
    canonical_name: str
    mention: str | None = None
    resolution_type: str | None = None


@dataclass(frozen=True)
class SkillEvidence:
    job_skill_id: uuid.UUID
    job_skill_name: str
    kind: EvidenceKind
    candidate_skill_id: uuid.UUID | None
    candidate_skill_name: str | None
    candidate_mention: str | None
    hops: int | None
    via_alias: bool
    preferred: bool = False


def candidate_mention(ref: SkillRef) -> str:
    return (ref.mention or ref.canonical_name).strip()


def collect_required_evidence(
    graph: SkillGraph,
    *,
    required: list[SkillRef],
    candidate_skills: list[SkillRef],
    ontology_version: str,
) -> list[SkillEvidence]:
    return [
        _best_evidence(
            graph,
            job=job,
            candidate_skills=candidate_skills,
            ontology_version=ontology_version,
            preferred=False,
        )
        for job in _unique(required)
    ]


def collect_preferred_evidence(
    graph: SkillGraph,
    *,
    preferred: list[SkillRef],
    candidate_skills: list[SkillRef],
    ontology_version: str,
) -> list[SkillEvidence]:
    return [
        _best_evidence(
            graph,
            job=job,
            candidate_skills=candidate_skills,
            ontology_version=ontology_version,
            preferred=True,
        )
        for job in _unique(preferred)
    ]


def _best_evidence(
    graph: SkillGraph,
    *,
    job: SkillRef,
    candidate_skills: list[SkillRef],
    ontology_version: str,
    preferred: bool,
) -> SkillEvidence:
    unique_candidate = _unique(candidate_skills)
    best: SkillEvidence | None = None
    for candidate in unique_candidate:
        view = classify_relationship(
            graph,
            job_skill_id=job.skill_id,
            job_skill_name=job.canonical_name,
            candidate_skill_id=candidate.skill_id,
            candidate_skill_name=candidate.canonical_name,
            ontology_version=ontology_version,
        )
        kind: EvidenceKind
        if view.evidence_type == "none":
            continue
        kind = view.evidence_type  # type: ignore[assignment]
        via_alias = kind == "exact" and _is_alias(candidate)
        item = SkillEvidence(
            job_skill_id=job.skill_id,
            job_skill_name=job.canonical_name,
            kind=kind,
            candidate_skill_id=candidate.skill_id,
            candidate_skill_name=candidate.canonical_name,
            candidate_mention=candidate_mention(candidate),
            hops=view.hops,
            via_alias=via_alias,
            preferred=preferred,
        )
        if best is None or _RANK[item.kind] < _RANK[best.kind]:
            best = item
        elif best is not None and item.kind == best.kind and item.via_alias and not best.via_alias:
            best = item
    if best is not None:
        return best
    return SkillEvidence(
        job_skill_id=job.skill_id,
        job_skill_name=job.canonical_name,
        kind="missing",
        candidate_skill_id=None,
        candidate_skill_name=None,
        candidate_mention=None,
        hops=None,
        via_alias=False,
        preferred=preferred,
    )


def _is_alias(ref: SkillRef) -> bool:
    return (ref.resolution_type or "").lower() == "alias"


def _unique(skills: list[SkillRef]) -> list[SkillRef]:
    seen: set[uuid.UUID] = set()
    ordered: list[SkillRef] = []
    for item in skills:
        if item.skill_id in seen:
            continue
        seen.add(item.skill_id)
        ordered.append(item)
    return ordered
