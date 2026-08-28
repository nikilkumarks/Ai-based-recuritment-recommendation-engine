"""Heuristic potential / gap-closability. Not hiring probability and not current match."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from app.models import CandidateProfile, CertificationItem
from app.modules.matching.composer import ComponentScore, clamp_score
from app.modules.matching.constants import SCORE_DECIMALS
from app.modules.matching.evidence import SkillEvidence, SkillRef
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.policies import classify_relationship
from app.modules.ontology.resolver import OntologyIndex

PotentialStatus = Literal["available", "not_applicable"]


@dataclass(frozen=True)
class PotentialPolicy:
    """Heuristic closability weights. Not empirically validated."""

    weight_set_version: str
    max_graph_distance: int
    exact: float
    child: float
    parent: float
    related: float
    similar: float
    two_hop_factor: float
    required_gap_weight: float
    preferred_gap_weight: float
    graph: float
    adjacent: float
    projects: float
    experience: float
    certifications: float
    semantic: float
    semantic_cosine_threshold: float
    recency_recent_days: int
    recency_stale_days: int
    recency_stale_factor: float


def default_potential_policy() -> PotentialPolicy:
    return PotentialPolicy(
        weight_set_version="potential-weights-v1",
        max_graph_distance=2,
        exact=1.0,
        child=0.8,
        parent=0.5,
        related=0.6,
        similar=0.5,
        two_hop_factor=0.5,
        required_gap_weight=0.85,
        preferred_gap_weight=0.15,
        graph=0.40,
        adjacent=0.20,
        projects=0.15,
        experience=0.15,
        certifications=0.05,
        semantic=0.05,
        semantic_cosine_threshold=0.45,
        recency_recent_days=730,
        recency_stale_days=1825,
        recency_stale_factor=0.7,
    )


def potential_policy_from_settings() -> PotentialPolicy:
    from app.core.config import get_settings

    settings = get_settings()
    base = default_potential_policy()
    return PotentialPolicy(
        weight_set_version=settings.potential_weight_set_version or base.weight_set_version,
        max_graph_distance=settings.potential_max_graph_distance,
        exact=settings.potential_weight_exact,
        child=settings.potential_weight_child,
        parent=settings.potential_weight_parent,
        related=settings.potential_weight_related,
        similar=settings.potential_weight_similar,
        two_hop_factor=settings.potential_two_hop_factor,
        required_gap_weight=base.required_gap_weight,
        preferred_gap_weight=base.preferred_gap_weight,
        graph=settings.potential_component_graph,
        adjacent=settings.potential_component_adjacent,
        projects=settings.potential_component_projects,
        experience=settings.potential_component_experience,
        certifications=settings.potential_component_certifications,
        semantic=settings.potential_component_semantic,
        semantic_cosine_threshold=settings.potential_semantic_cosine_threshold,
        recency_recent_days=base.recency_recent_days,
        recency_stale_days=base.recency_stale_days,
        recency_stale_factor=base.recency_stale_factor,
    )


@dataclass(frozen=True)
class GapClosability:
    skill_id: uuid.UUID
    skill_name: str
    required: bool
    current_kind: str
    distance: int | None
    relation: str | None
    candidate_skill_id: uuid.UUID | None
    candidate_skill_name: str | None
    path: tuple[uuid.UUID, ...]
    graph_score: float
    adjacent: bool


@dataclass(frozen=True)
class PotentialResult:
    potential: float | None
    status: PotentialStatus
    components: tuple[ComponentScore, ...]
    gaps: tuple[GapClosability, ...]
    adjacent_skill_ratio: float | None
    traces: tuple[dict[str, Any], ...]
    features: dict[str, Any]


def assess_potential(
    *,
    graph: SkillGraph,
    index: OntologyIndex,
    ontology_version: str,
    required: list[SkillEvidence],
    preferred: list[SkillEvidence],
    candidate_skills: list[SkillRef],
    profile: CandidateProfile,
    policy: PotentialPolicy,
    semantic: dict[str, Any],
) -> PotentialResult:
    """Closability of remaining required gaps. Does not change current_match."""
    required_gaps = [item for item in required if item.kind != "exact"]
    preferred_gaps = [item for item in preferred if item.kind != "exact"]
    if not required_gaps:
        return _not_applicable(policy)
    required_close = [
        _closability(
            graph,
            index,
            ontology_version=ontology_version,
            evidence=item,
            candidate_skills=candidate_skills,
            policy=policy,
            required=True,
        )
        for item in required_gaps
    ]
    preferred_close = [
        _closability(
            graph,
            index,
            ontology_version=ontology_version,
            evidence=item,
            candidate_skills=candidate_skills,
            policy=policy,
            required=False,
        )
        for item in preferred_gaps
    ]
    graph_required = _mean([item.graph_score for item in required_close])
    graph_preferred = _mean([item.graph_score for item in preferred_close])
    graph_value = clamp_score(
        graph_required * policy.required_gap_weight
        + (graph_preferred if graph_preferred is not None else 0.0) * policy.preferred_gap_weight
    )
    adjacent_ratio = _adjacent_ratio(required_close)
    project_score, project_available, project_traces = _artifact_evidence(
        kind="project",
        items=list(profile.project_items),
        gaps=required_close,
        index=index,
        policy=policy,
        cosine=semantic.get("relevant_project_cosine"),
        cosine_available=bool(semantic.get("semantic_similarity_available")),
    )
    experience_score, experience_available, experience_traces = _artifact_evidence(
        kind="experience",
        items=list(profile.experience_items),
        gaps=required_close,
        index=index,
        policy=policy,
        cosine=semantic.get("relevant_experience_cosine"),
        cosine_available=bool(semantic.get("semantic_similarity_available")),
    )
    cert_score, cert_available, cert_traces = _certification_evidence(
        list(profile.certification_items),
        required_close,
        index,
        policy,
    )
    semantic_raw = semantic.get("profile_job_cosine")
    semantic_available = bool(semantic.get("semantic_similarity_available")) and isinstance(
        semantic_raw, (int, float)
    )
    semantic_value = 0.0
    if semantic_available:
        semantic_value = _semantic_support(float(semantic_raw), policy)

    parts = [
        ComponentScore("graph_closability", graph_value, policy.graph, True),
        ComponentScore("adjacent_skill_ratio", adjacent_ratio, policy.adjacent, True),
        ComponentScore("project_evidence", project_score or 0.0, policy.projects, project_available),
        ComponentScore(
            "experience_evidence",
            experience_score or 0.0,
            policy.experience,
            experience_available,
        ),
        ComponentScore(
            "certification_evidence",
            cert_score or 0.0,
            policy.certifications,
            cert_available,
        ),
        ComponentScore("semantic_evidence", semantic_value, policy.semantic, semantic_available),
    ]
    used = [item for item in parts if item.available and item.weight > 0]
    weight_sum = sum(item.weight for item in used)
    if weight_sum <= 0:
        score = 0.0
    else:
        score = sum(item.value * item.weight for item in used) / weight_sum
    traces = _graph_traces(required_close, ontology_version) + project_traces + experience_traces + cert_traces
    if semantic_available:
        traces.append(
            {
                "type": "potential_semantic",
                "cosine": round(float(semantic_raw), 5),
                "threshold": policy.semantic_cosine_threshold,
                "role": "supporting_heuristic",
            }
        )
    features = {
        "feature_schema_version": "feature-schema-v2",
        "potential_status": "available",
        "potential": clamp_score(score),
        "potential_weight_set_version": policy.weight_set_version,
        "potential_max_graph_distance": policy.max_graph_distance,
        "potential_graph_closability": graph_value,
        "potential_adjacent_skill_ratio": adjacent_ratio,
        "potential_project_evidence": project_score,
        "potential_experience_evidence": experience_score,
        "potential_certification_evidence": cert_score,
        "potential_semantic_evidence": semantic_value if semantic_available else None,
        "potential_required_gap_count": len(required_close),
        "potential_preferred_gap_count": len(preferred_close),
        "potential_required_dominates_preferred": True,
    }
    return PotentialResult(
        potential=clamp_score(score),
        status="available",
        components=tuple(parts),
        gaps=tuple(required_close + preferred_close),
        adjacent_skill_ratio=adjacent_ratio,
        traces=tuple(traces),
        features=features,
    )


def _not_applicable(policy: PotentialPolicy) -> PotentialResult:
    features = {
        "feature_schema_version": "feature-schema-v2",
        "potential_status": "not_applicable",
        "potential": None,
        "potential_weight_set_version": policy.weight_set_version,
        "potential_max_graph_distance": policy.max_graph_distance,
        "potential_graph_closability": None,
        "potential_adjacent_skill_ratio": None,
        "potential_project_evidence": None,
        "potential_experience_evidence": None,
        "potential_certification_evidence": None,
        "potential_semantic_evidence": None,
        "potential_required_gap_count": 0,
        "potential_preferred_gap_count": 0,
        "potential_required_dominates_preferred": True,
    }
    return PotentialResult(
        potential=None,
        status="not_applicable",
        components=(),
        gaps=(),
        adjacent_skill_ratio=None,
        traces=(),
        features=features,
    )


def _closability(
    graph: SkillGraph,
    index: OntologyIndex,
    *,
    ontology_version: str,
    evidence: SkillEvidence,
    candidate_skills: list[SkillRef],
    policy: PotentialPolicy,
    required: bool,
) -> GapClosability:
    best_skill = None
    best_name = evidence.candidate_skill_name
    path: tuple[uuid.UUID, ...] = ()
    distance = evidence.hops
    relation = evidence.kind if evidence.kind != "missing" else None
    if evidence.candidate_skill_id is not None:
        best_skill = evidence.candidate_skill_id
        found = graph.shortest_path(evidence.candidate_skill_id, evidence.job_skill_id)
        if found:
            path = tuple(found)
            distance = len(found) - 1
    if evidence.kind == "missing" or best_skill is None:
        for candidate in candidate_skills:
            found = graph.shortest_path(candidate.skill_id, evidence.job_skill_id)
            if not found:
                continue
            hops = len(found) - 1
            if distance is None or hops < distance:
                distance = hops
                path = tuple(found)
                best_skill = candidate.skill_id
                best_name = candidate.canonical_name
                if hops == 1:
                    view = classify_relationship(
                        graph,
                        job_skill_id=evidence.job_skill_id,
                        job_skill_name=evidence.job_skill_name,
                        candidate_skill_id=candidate.skill_id,
                        candidate_skill_name=candidate.canonical_name,
                        ontology_version=ontology_version,
                    )
                    relation = view.evidence_type if view.evidence_type != "none" else graph.hop_kind(
                        candidate.skill_id, evidence.job_skill_id
                    )
                elif hops > 1:
                    relation = "two_hop"
    if evidence.kind in {"child", "parent", "related"} and (distance is None or distance <= 1):
        relation = evidence.kind
        distance = evidence.hops if evidence.hops is not None else 1
    if distance is not None and distance > policy.max_graph_distance:
        distance = None
        path = ()
        relation = None
        graph_score = 0.0
        adjacent = False
    else:
        graph_score = _relation_score(relation, distance, policy)
        adjacent = distance == 1 or evidence.kind in {"child", "parent", "related"}
    return GapClosability(
        skill_id=evidence.job_skill_id,
        skill_name=evidence.job_skill_name,
        required=required,
        current_kind=evidence.kind,
        distance=distance,
        relation=relation,
        candidate_skill_id=best_skill,
        candidate_skill_name=best_name,
        path=path,
        graph_score=graph_score,
        adjacent=adjacent,
    )


def _relation_score(relation: str | None, distance: int | None, policy: PotentialPolicy) -> float:
    if distance == 0:
        return policy.exact
    if relation == "child":
        base = policy.child
    elif relation == "parent":
        base = policy.parent
    elif relation == "related":
        base = policy.related
    elif relation == "similar":
        base = policy.similar
    elif relation == "two_hop":
        base = max(policy.related, policy.parent) * policy.two_hop_factor
    else:
        return 0.0
    if distance is not None and distance >= 2:
        base *= policy.two_hop_factor
    return clamp_score(base)


def _adjacent_ratio(gaps: list[GapClosability]) -> float:
    if not gaps:
        return 0.0
    return clamp_score(sum(1 for item in gaps if item.adjacent) / len(gaps))


def _artifact_evidence(
    *,
    kind: str,
    items: list[Any],
    gaps: list[GapClosability],
    index: OntologyIndex,
    policy: PotentialPolicy,
    cosine: object,
    cosine_available: bool,
) -> tuple[float | None, bool, list[dict[str, Any]]]:
    if not items:
        return None, False, []
    scores: list[float] = []
    traces: list[dict[str, Any]] = []
    cosine_hit = (
        cosine_available
        and isinstance(cosine, (int, float))
        and float(cosine) >= policy.semantic_cosine_threshold
    )
    for item in items:
        text = _item_text(item)
        recency = _recency_factor(item, policy)
        for gap in gaps:
            names = _gap_vocab(gap, index)
            text_hit = any(name and name.casefold() in text.casefold() for name in names)
            if not text_hit and not cosine_hit:
                continue
            value = 0.7 if text_hit else 0.0
            if cosine_hit:
                value = max(value, min(1.0, float(cosine)))
            value *= recency
            scores.append(value)
            traces.append(
                {
                    "type": f"potential_{kind}",
                    "missing_skill": gap.skill_name,
                    kind: getattr(item, "name", None) or getattr(item, "job_title", None),
                    "evidence": "text_overlap" if text_hit else "embedding_cosine_heuristic",
                    "recency_factor": recency,
                }
            )
            break
    if not scores:
        return 0.0, True, []
    return clamp_score(max(scores)), True, traces


def _certification_evidence(
    items: list[CertificationItem],
    gaps: list[GapClosability],
    index: OntologyIndex,
    policy: PotentialPolicy,
) -> tuple[float | None, bool, list[dict[str, Any]]]:
    if not items:
        return None, False, []
    traces: list[dict[str, Any]] = []
    scores: list[float] = []
    for cert in items:
        text = f"{cert.name} {cert.issuing_organization or ''}"
        recency = _recency_factor(cert, policy)
        for gap in gaps:
            names = _gap_vocab(gap, index)
            if not any(name and name.casefold() in text.casefold() for name in names):
                continue
            scores.append(0.6 * recency)
            traces.append(
                {
                    "type": "potential_certification",
                    "missing_skill": gap.skill_name,
                    "certification": cert.name,
                    "evidence": "name_overlap",
                }
            )
            break
    if not scores:
        return 0.0, True, []
    return clamp_score(max(scores)), True, traces


def _semantic_support(cosine: float, policy: PotentialPolicy) -> float:
    if cosine < policy.semantic_cosine_threshold:
        return 0.0
    return clamp_score(max(0.0, min(1.0, cosine)))


def _item_text(item: object) -> str:
    parts = [
        getattr(item, "name", None),
        getattr(item, "job_title", None),
        getattr(item, "description", None),
        getattr(item, "employer", None),
    ]
    return " ".join(str(part) for part in parts if part)


def _recency_factor(item: object, policy: PotentialPolicy) -> float:
    stamp = getattr(item, "end_date", None) or getattr(item, "start_date", None)
    stamp = stamp or getattr(item, "issue_date", None)
    if stamp is None:
        return 1.0
    if not isinstance(stamp, date):
        return 1.0
    age = (date.today() - stamp).days
    if age <= policy.recency_recent_days:
        return 1.0
    if age >= policy.recency_stale_days:
        return policy.recency_stale_factor
    return 1.0


def _gap_vocab(gap: GapClosability, index: OntologyIndex) -> list[str]:
    names = [gap.skill_name]
    if gap.candidate_skill_name:
        names.append(gap.candidate_skill_name)
    record = index.skills.get(gap.skill_id)
    if record is not None:
        names.append(record.canonical_name)
    if gap.candidate_skill_id is not None:
        other = index.skills.get(gap.candidate_skill_id)
        if other is not None:
            names.append(other.canonical_name)
    return names


def _graph_traces(gaps: list[GapClosability], ontology_version: str) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for item in gaps:
        traces.append(
            {
                "type": "potential_gap",
                "missing_skill": item.skill_name,
                "current_kind": item.current_kind,
                "required": item.required,
            }
        )
        if item.adjacent and item.candidate_skill_name:
            traces.append(
                {
                    "type": "potential_adjacent",
                    "missing_skill": item.skill_name,
                    "candidate_skill": item.candidate_skill_name,
                    "relation": _relation_label(item.relation),
                    "distance": item.distance,
                    "ontology_version": ontology_version,
                }
            )
        if item.path and item.distance:
            traces.append(
                {
                    "type": "potential_graph_path",
                    "missing_skill": item.skill_name,
                    "distance": item.distance,
                    "path_skill_ids": [str(skill_id) for skill_id in item.path],
                    "ontology_version": ontology_version,
                }
            )
    return traces


def _relation_label(relation: str | None) -> str:
    mapping = {
        "related": "related_to",
        "similar": "similar_to",
        "child": "child_of",
        "parent": "parent_of",
        "two_hop": "two_hop",
    }
    return mapping.get(relation or "", relation or "unknown")


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return clamp_score(sum(values) / len(values))
