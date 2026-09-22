"""TEST FIXTURE ONLY. Not project training data and not production metrics."""

from __future__ import annotations

from typing import Any

FIXTURE_MARK = "TEST FIXTURE ONLY"


def fixture_rows(n_jobs: int = 6, per_job: int = 10) -> list[dict[str, Any]]:
    """Deterministic labeled rows for pipeline plumbing. Do not publish as project accuracy."""
    rows: list[dict[str, Any]] = []
    for job_n in range(n_jobs):
        for cand_n in range(per_job):
            coverage = round((cand_n + 1) / per_job, 4)
            cosine = round(0.2 + 0.6 * coverage, 4)
            current = round(0.25 * coverage + 0.05, 4)
            label = 1 if coverage >= 0.5 else 0
            candidate_id = f"fixture-c-{job_n}-{cand_n}"
            job_id = f"fixture-j-{job_n}"
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "job_id": job_id,
                    "label": label,
                    "decision_time": "2026-01-02T00:00:00+00:00",
                    "feature_schema_version": "feature-schema-v2",
                    "ontology_version": "seed-0.1",
                    "embedding_model_name": "hashing-encoder",
                    "embedding_model_version": "hashing-v1",
                    "embedding_text_version": "embedding-text-v1",
                    "test_fixture_only": True,
                    "grouping": {"job_id": job_id},
                    "features": {
                        "required_skill_coverage": coverage,
                        "preferred_skill_coverage": 0.5,
                        "required_skill_count": 4,
                        "matched_required_skill_count": int(round(coverage * 4)),
                        "missing_required_skill_count": 4 - int(round(coverage * 4)),
                        "related_required_skill_count": 0,
                        "partial_required_skill_count": 0,
                        "parent_required_skill_count": 0,
                        "preferred_skill_count": 1,
                        "matched_preferred_skill_count": 1 if coverage > 0.3 else 0,
                        "exact_alias_matches": 0,
                        "parent_matches": 0,
                        "child_matches": 0,
                        "related_matches": 0,
                        "average_gap_distance": None,
                        "semantic_similarity_available": True,
                        "profile_job_cosine": cosine,
                        "current_match": current,
                        "candidate_experience_years": 3.0,
                        "required_experience_years": 2.0,
                        "experience_satisfied": True,
                        "experience_evidence_present": True,
                        "education_requirement_present": True,
                        "education_alignment": True,
                        "candidate_project_count": 1,
                        "relevant_project_count": 1 if coverage > 0.4 else 0,
                        "project_evidence_present": coverage > 0.4,
                        "relevant_project_cosine": cosine,
                        "potential": 0.4 if coverage < 1 else None,
                        "potential_status": "available" if coverage < 1 else "not_applicable",
                        "potential_graph_closability": 0.3,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                }
            )
    return rows
