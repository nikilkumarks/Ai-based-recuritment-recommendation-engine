"""Suggested skill paths. Ontology shortest paths only; not a guaranteed career path."""

from __future__ import annotations

import uuid
from typing import Any

from app.modules.matching.evidence import SkillRef
from app.modules.matching.potential import GapClosability
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.resolver import OntologyIndex


def suggested_paths_for_gaps(
    *,
    graph: SkillGraph,
    index: OntologyIndex,
    gaps: list[GapClosability] | tuple[GapClosability, ...],
    candidate_skills: list[SkillRef],
    max_distance: int,
) -> list[dict[str, Any]]:
    """Bounded paths from an owned skill toward a remaining required gap."""
    owned = {item.skill_id for item in candidate_skills}
    paths: list[dict[str, Any]] = []
    for gap in gaps:
        if not gap.required:
            continue
        if gap.current_kind == "exact":
            continue
        chosen: list[uuid.UUID] | None = list(gap.path) if gap.path else None
        if chosen is None:
            chosen = _best_path(graph, owned, gap.skill_id)
        if not chosen or len(chosen) - 1 > max_distance:
            continue
        steps = [_step(index, skill_id) for skill_id in chosen]
        if any(step is None for step in steps):
            continue
        paths.append(
            {
                "target_skill": gap.skill_name,
                "target_skill_id": str(gap.skill_id),
                "distance": len(chosen) - 1,
                "relation": gap.relation,
                "label": "Suggested Skill Path",
                "steps": steps,
            }
        )
    return paths


def suggested_growth_neighbors(
    *,
    graph: SkillGraph,
    index: OntologyIndex,
    candidate_skills: list[SkillRef],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """1-hop neighbors the candidate does not already have. Not job-targeted."""
    owned = {item.skill_id for item in candidate_skills}
    seen: set[uuid.UUID] = set()
    items: list[dict[str, Any]] = []
    for skill in candidate_skills:
        neighbors = (
            *graph.related_ids(skill.skill_id),
            *graph.similar_ids(skill.skill_id),
            *graph.child_ids(skill.skill_id),
        )
        for nxt in neighbors:
            if nxt in owned or nxt in seen:
                continue
            seen.add(nxt)
            record = index.skills.get(nxt)
            if record is None:
                continue
            items.append(
                {
                    "target_skill": record.canonical_name,
                    "target_skill_id": str(nxt),
                    "distance": 1,
                    "relation": graph.hop_kind(skill.skill_id, nxt),
                    "label": "Suggested Skill Path",
                    "steps": [
                        _step(index, skill.skill_id),
                        _step(index, nxt),
                    ],
                }
            )
            if len(items) >= limit:
                return items
    return items


def _best_path(graph: SkillGraph, owned: set[uuid.UUID], target: uuid.UUID) -> list[uuid.UUID] | None:
    best: list[uuid.UUID] | None = None
    for skill_id in owned:
        found = graph.shortest_path(skill_id, target)
        if not found:
            continue
        if best is None or len(found) < len(best):
            best = found
    return best


def _step(index: OntologyIndex, skill_id: uuid.UUID) -> dict[str, str] | None:
    record = index.skills.get(skill_id)
    if record is None:
        return None
    return {"skill": record.canonical_name, "skill_id": str(skill_id)}
