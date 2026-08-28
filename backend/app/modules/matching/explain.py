"""Structured explanation traces. No LLM prose."""

from __future__ import annotations

from typing import Any

from app.modules.matching.evidence import SkillEvidence


def skill_traces(
    *,
    required: list[SkillEvidence],
    preferred: list[SkillEvidence],
    ontology_version: str,
) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for item in required:
        traces.append(_required_trace(item, ontology_version))
    for item in preferred:
        if item.kind == "exact":
            traces.append(
                {
                    "type": "preferred_skill",
                    "preferred_skill": item.job_skill_name,
                    "candidate_evidence": item.candidate_mention,
                    "canonical_skill_id": str(item.job_skill_id),
                    "ontology_version": ontology_version,
                }
            )
    return traces


def _required_trace(item: SkillEvidence, ontology_version: str) -> dict[str, Any]:
    if item.kind == "exact" and item.via_alias:
        trace_type = "alias_match"
    elif item.kind == "exact":
        trace_type = "exact_match"
    elif item.kind == "child":
        trace_type = "hierarchy_child"
    elif item.kind == "parent":
        trace_type = "hierarchy_parent"
    elif item.kind == "related":
        trace_type = "related_skill"
    else:
        trace_type = "missing_skill"
    payload: dict[str, Any] = {
        "type": trace_type,
        "required_skill": item.job_skill_name,
        "canonical_skill_id": str(item.job_skill_id),
        "ontology_version": ontology_version,
    }
    if item.candidate_mention:
        payload["candidate_evidence"] = item.candidate_mention
    if item.candidate_skill_id is not None:
        payload["candidate_skill_id"] = str(item.candidate_skill_id)
    if item.candidate_skill_name:
        payload["candidate_skill_name"] = item.candidate_skill_name
    if item.hops is not None:
        payload["hops"] = item.hops
    return payload


def extra_traces(
    *,
    semantic_available: bool,
    semantic_similarity: float | None,
    experience_satisfied: bool | None,
    required_experience_years: float | None,
    candidate_experience_years: float | None,
    education_requirement_present: bool,
    education_alignment: bool | None,
    relevant_project_count: int,
    project_evidence_present: bool,
) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    if semantic_available and semantic_similarity is not None:
        traces.append(
            {
                "type": "semantic_similarity",
                "cosine": semantic_similarity,
                "role": "feature",
            }
        )
    if required_experience_years is not None:
        if experience_satisfied is True:
            traces.append(
                {
                    "type": "experience_match",
                    "required_years": required_experience_years,
                    "candidate_years": candidate_experience_years,
                }
            )
        elif experience_satisfied is False:
            traces.append(
                {
                    "type": "experience_gap",
                    "required_years": required_experience_years,
                    "candidate_years": candidate_experience_years,
                }
            )
        else:
            traces.append(
                {
                    "type": "experience_unknown",
                    "required_years": required_experience_years,
                    "candidate_years": None,
                }
            )
    if education_requirement_present and education_alignment is True:
        traces.append({"type": "education_match", "aligned": True})
    if project_evidence_present and relevant_project_count > 0:
        traces.append(
            {
                "type": "project_evidence",
                "relevant_project_count": relevant_project_count,
            }
        )
    return traces
