"""Dataset validation for offline training. Does not fabricate rows."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.modules.features.schema import (
    SUPPORTED_SNAPSHOT_SCHEMAS,
    vectorize_features,
)
from ml.leakage import leakage_errors

INSUFFICIENT_MESSAGE = "Insufficient real labeled data for training experiment."


def validate_dataset(
    rows: list[dict[str, Any]],
    *,
    min_rows: int,
    min_positives: int,
    min_negatives: int,
    min_jobs: int,
    allow_insufficient: bool = False,
) -> dict[str, Any]:
    """Return a report. Training must skip when eligible is False."""
    vectors: list[list[float]] = []
    labels: list[int] = []
    groups: list[str] = []
    excluded: Counter[str] = Counter()
    schemas: set[str] = set()
    ontologies: set[str] = set()
    for row in rows:
        label = row.get("label")
        if label not in {0, 1}:
            excluded["invalid_label"] += 1
            continue
        schema = row.get("feature_schema_version")
        if schema not in SUPPORTED_SNAPSHOT_SCHEMAS:
            excluded["invalid_schema"] += 1
            continue
        if not row.get("ontology_version"):
            excluded["unknown_ontology_version"] += 1
            continue
        grouping = row.get("grouping") or {}
        job_id = str(grouping.get("job_id") or row.get("job_id") or "")
        if not job_id:
            excluded["missing_job_group"] += 1
            continue
        features = dict(row.get("features") or {})
        vector, error = vectorize_features(features)
        if error or not vector:
            excluded[error or "invalid_feature_values"] += 1
            continue
        schemas.add(str(schema))
        ontologies.add(str(row.get("ontology_version")))
        vectors.append(vector)
        labels.append(int(label))
        groups.append(job_id)
    leak = leakage_errors(rows)
    positives = sum(labels)
    negatives = len(labels) - positives
    unique_jobs = len(set(groups))
    reasons: list[str] = []
    if leak:
        reasons.extend(leak)
    if len(vectors) < min_rows:
        reasons.append(f"min_training_rows:{len(vectors)}<{min_rows}")
    if positives < min_positives:
        reasons.append(f"min_positive_labels:{positives}<{min_positives}")
    if negatives < min_negatives:
        reasons.append(f"min_negative_labels:{negatives}<{min_negatives}")
    if unique_jobs < min_jobs:
        reasons.append(f"min_unique_jobs:{unique_jobs}<{min_jobs}")
    eligible = not reasons or allow_insufficient
    if leak:
        eligible = False
    return {
        "eligible": eligible and not leak,
        "message": INSUFFICIENT_MESSAGE if reasons and not leak else None,
        "reasons": reasons,
        "row_count": len(vectors),
        "positive_count": positives,
        "negative_count": negatives,
        "positive_ratio": (positives / len(vectors)) if vectors else 0.0,
        "negative_ratio": (negatives / len(vectors)) if vectors else 0.0,
        "unique_jobs": unique_jobs,
        "excluded": dict(excluded),
        "feature_schema_versions": sorted(schemas),
        "ontology_versions": sorted(ontologies),
        "X": vectors,
        "y": labels,
        "groups": groups,
        "leakage": leak,
    }
