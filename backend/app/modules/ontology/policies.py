"""Hierarchy and relatedness policies. Not match scores.

Job requires Machine Learning, candidate has Deep Learning
  → child evidence (partial/related). Not exact mastery.

Job requires Deep Learning, candidate has Machine Learning
  → parent evidence (weak). Not equivalent to Deep Learning.

Job requires Kubernetes, candidate has Docker
  → related_skill. Not exact or alias match.

Skill normalization is not candidate-job matching.
"""

from __future__ import annotations

import uuid

from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.schemas import SkillRelationshipView


def classify_relationship(
    graph: SkillGraph,
    *,
    job_skill_id: uuid.UUID,
    job_skill_name: str,
    candidate_skill_id: uuid.UUID,
    candidate_skill_name: str,
    ontology_version: str,
) -> SkillRelationshipView:
    if job_skill_id == candidate_skill_id:
        return SkillRelationshipView(
            job_skill_id=job_skill_id,
            job_skill_name=job_skill_name,
            candidate_skill_id=candidate_skill_id,
            candidate_skill_name=candidate_skill_name,
            evidence_type="exact",
            hops=0,
            ontology_version=ontology_version,
        )
    child_hops = graph.hops(graph.children, job_skill_id, candidate_skill_id)
    if child_hops:
        return SkillRelationshipView(
            job_skill_id=job_skill_id,
            job_skill_name=job_skill_name,
            candidate_skill_id=candidate_skill_id,
            candidate_skill_name=candidate_skill_name,
            evidence_type="child",
            hops=child_hops,
            ontology_version=ontology_version,
        )
    parent_hops = graph.hops(graph.parents, job_skill_id, candidate_skill_id)
    if parent_hops:
        return SkillRelationshipView(
            job_skill_id=job_skill_id,
            job_skill_name=job_skill_name,
            candidate_skill_id=candidate_skill_id,
            candidate_skill_name=candidate_skill_name,
            evidence_type="parent",
            hops=parent_hops,
            ontology_version=ontology_version,
        )
    if candidate_skill_id in graph.related_ids(job_skill_id):
        return SkillRelationshipView(
            job_skill_id=job_skill_id,
            job_skill_name=job_skill_name,
            candidate_skill_id=candidate_skill_id,
            candidate_skill_name=candidate_skill_name,
            evidence_type="related",
            hops=1,
            ontology_version=ontology_version,
        )
    return SkillRelationshipView(
        job_skill_id=job_skill_id,
        job_skill_name=job_skill_name,
        candidate_skill_id=candidate_skill_id,
        candidate_skill_name=candidate_skill_name,
        evidence_type="none",
        hops=None,
        ontology_version=ontology_version,
    )
