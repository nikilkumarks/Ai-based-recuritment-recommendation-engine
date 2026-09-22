"""Leakage guards for shortlist training. Fail closed."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.modules.features.schema import FORBIDDEN_FEATURE_KEYS, ordered_feature_names


def leakage_errors(rows: list[dict[str, Any]], feature_names: list[str] | None = None) -> list[str]:
    names = feature_names or ordered_feature_names()
    lowered = {name.lower() for name in names}
    errors: list[str] = []
    if lowered & {key.lower() for key in FORBIDDEN_FEATURE_KEYS}:
        errors.append("forbidden_feature_in_vector")
    if "label" in lowered:
        errors.append("label_in_feature_vector")
    if "job_id" in lowered or "candidate_id" in lowered:
        errors.append("id_in_feature_vector")
    for row in rows:
        features = row.get("features") or {}
        if not isinstance(features, dict):
            errors.append("invalid_feature_payload")
            continue
        for key in features:
            if str(key).lower() in FORBIDDEN_FEATURE_KEYS:
                errors.append(f"forbidden_key_in_snapshot:{key}")
                break
        decision_time = _parse_time(row.get("decision_time"))
        snap_time = _parse_time((row.get("features") or {}).get("created_at")) or _parse_time(
            row.get("snapshot_created_at")
        )
        if decision_time is not None and snap_time is not None and snap_time > decision_time:
            errors.append("future_feature_snapshot")
            break
        if row.get("label") in features.values() and "label" in features:
            errors.append("label_copied_into_features")
            break
    return list(dict.fromkeys(errors))


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
