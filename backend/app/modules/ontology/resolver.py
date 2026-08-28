"""Deterministic skill resolver. Does not invent canonical skills."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.core.config import get_settings
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.normalize import normalize_lookup
from app.modules.ontology.schemas import SkillNormalizationResult


@dataclass(frozen=True)
class SkillRecord:
    id: uuid.UUID
    canonical_name: str
    slug: str
    status: str
    lookup: str


@dataclass
class OntologyIndex:
    version: str
    checksum: str
    skills: dict[uuid.UUID, SkillRecord]
    canonical_lookup: dict[str, uuid.UUID]
    exact_alias: dict[str, uuid.UUID]
    normalized_alias: dict[str, uuid.UUID]
    children: dict[uuid.UUID, tuple[uuid.UUID, ...]]
    parents: dict[uuid.UUID, tuple[uuid.UUID, ...]]
    related: dict[uuid.UUID, tuple[uuid.UUID, ...]]
    similar: dict[uuid.UUID, tuple[uuid.UUID, ...]] = field(default_factory=dict)
    fuzzy_choices: tuple[tuple[str, uuid.UUID], ...] = field(default_factory=tuple)

    def graph(self, max_depth: int) -> SkillGraph:
        return SkillGraph(
            children=self.children,
            parents=self.parents,
            related=self.related,
            similar=self.similar,
            max_depth=max_depth,
        )


def resolve_skill(
    mention: str,
    index: OntologyIndex,
    *,
    source_section: str | None = None,
    evidence: str | None = None,
    start: int | None = None,
    end: int | None = None,
    fuzzy_threshold: float | None = None,
) -> SkillNormalizationResult:
    settings = get_settings()
    threshold = settings.ontology_fuzzy_threshold if fuzzy_threshold is None else fuzzy_threshold
    lookup = normalize_lookup(mention)
    raw = mention.strip()
    proof = evidence if evidence is not None else raw
    unmatched = SkillNormalizationResult(
        raw_text=raw,
        normalized_text=lookup,
        resolution_type="unmatched",
        ontology_version=index.version,
        normalization_confidence=0,
        needs_review=True,
        source_section=source_section,
        evidence=proof,
        start=start,
        end=end,
    )
    if not lookup:
        return unmatched
    skill_id = index.canonical_lookup.get(lookup)
    if skill_id is not None:
        return _hit(index, skill_id, raw, lookup, "canonical", 1.0, source_section, proof, start, end)
    skill_id = index.exact_alias.get(raw.casefold())
    if skill_id is not None:
        return _hit(index, skill_id, raw, lookup, "alias", 0.95, source_section, proof, start, end)
    skill_id = index.normalized_alias.get(lookup)
    if skill_id is not None:
        return _hit(index, skill_id, raw, lookup, "alias", 0.93, source_section, proof, start, end)
    fuzzy = _fuzzy_resolve(lookup, index, threshold)
    if fuzzy is None:
        return unmatched
    skill_id, score = fuzzy
    return _hit(index, skill_id, raw, lookup, "fuzzy", score, source_section, proof, start, end)


def _hit(
    index: OntologyIndex,
    skill_id: uuid.UUID,
    raw: str,
    lookup: str,
    resolution: str,
    confidence: float,
    source_section: str | None,
    evidence: str,
    start: int | None,
    end: int | None,
) -> SkillNormalizationResult:
    skill = index.skills[skill_id]
    return SkillNormalizationResult(
        raw_text=raw,
        normalized_text=lookup,
        canonical_skill_id=skill.id,
        canonical_skill_name=skill.canonical_name,
        resolution_type=resolution,  # type: ignore[arg-type]
        ontology_version=index.version,
        normalization_confidence=round(min(max(confidence, 0), 1), 3),
        needs_review=resolution == "fuzzy",
        source_section=source_section,
        evidence=evidence,
        start=start,
        end=end,
    )


def _fuzzy_resolve(
    lookup: str, index: OntologyIndex, threshold: float
) -> tuple[uuid.UUID, float] | None:
    if threshold >= 1 or not index.fuzzy_choices or len(lookup) < 4:
        return None
    choices = [item[0] for item in index.fuzzy_choices]
    ranked = process.extract(lookup, choices, scorer=fuzz.ratio, limit=3)
    if not ranked:
        return None
    best_name, best_score, _ = ranked[0]
    score = best_score / 100.0
    if score < threshold:
        return None
    if len(ranked) > 1 and ranked[1][1] / 100.0 >= score - 0.02:
        return None
    mapping = {name: skill_id for name, skill_id in index.fuzzy_choices}
    skill_id = mapping.get(best_name)
    if skill_id is None:
        return None
    return skill_id, score
