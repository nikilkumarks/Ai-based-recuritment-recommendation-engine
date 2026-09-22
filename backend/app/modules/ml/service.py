"""Dataset snapshot construction. Does not train models or compute accuracy."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DatasetSnapshot, FeatureSnapshot, RecruiterDecision
from app.modules.applications.constants import BINARY_ACTIONS, DATASET_SNAPSHOT_CREATED
from app.modules.applications.repository import ApplicationsRepository
from app.modules.identity import audit
from app.modules.ml.policies import (
    BINARY_NEGATIVE,
    BINARY_POSITIVE,
    DATASET_SOURCE,
    GROUPING_KEYS,
    LABEL_POLICY_VERSION,
    LEAKAGE_KEYS,
    PROTECTED_KEYS,
    SUPPORTED_FEATURE_SCHEMAS,
)


class DatasetService:
    """Point-in-time training-row preparation. No XGBoost and no model artifacts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.decisions = ApplicationsRepository(db)

    def create_snapshot(self, *, actor_id: uuid.UUID | None) -> DatasetSnapshot:
        built = self.build_rows()
        checksum = _checksum(built["rows"])
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"dataset-v1-{stamp}-{checksum[:8]}-{uuid.uuid4().hex[:6]}"
        settings = get_settings()
        row = DatasetSnapshot(
            name=name,
            description=(
                "Point-in-time recruiter-decision dataset. "
                "Recruiter decisions are behavioral labels reflecting recruiter actions, "
                "not ground-truth hiring outcomes. No trained project model is produced "
                "until sufficient real labeled data exists."
            ),
            source=DATASET_SOURCE,
            row_count=len(built["rows"]),
            checksum=checksum,
            label_policy_version=LABEL_POLICY_VERSION,
            manifest={
                "label_policy_version": LABEL_POLICY_VERSION,
                "dataset_version": name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "min_training_rows": settings.min_training_rows,
                "sufficient_for_training_experiment": len(built["rows"])
                >= settings.min_training_rows,
                "positive_count": built["positive_count"],
                "negative_count": built["negative_count"],
                "positive_ratio": built["positive_ratio"],
                "negative_ratio": built["negative_ratio"],
                "excluded_count": built["excluded_count"],
                "exclusion_reasons": built["exclusion_reasons"],
                "feature_schema_versions": built["feature_schema_versions"],
                "ontology_versions": built["ontology_versions"],
                "embedding_versions": built["embedding_versions"],
                "source_decision_range": built["source_decision_range"],
                "grouping": "job_id",
                "trained": False,
            },
            rows=built["rows"],
        )
        self.db.add(row)
        self.db.flush()
        audit.record_audit(
            self.db,
            action=DATASET_SNAPSHOT_CREATED,
            resource_type="dataset_snapshot",
            actor_user_id=actor_id,
            resource_id=row.id,
            metadata={
                "name": name,
                "row_count": row.row_count,
                "positive_count": built["positive_count"],
                "negative_count": built["negative_count"],
            },
        )
        self.db.flush()
        return row

    def list_snapshots(self) -> list[DatasetSnapshot]:
        from sqlalchemy import select

        return list(
            self.db.scalars(select(DatasetSnapshot).order_by(DatasetSnapshot.created_at.desc())).all()
        )

    def get_snapshot(self, snapshot_id: uuid.UUID) -> DatasetSnapshot | None:
        return self.db.get(DatasetSnapshot, snapshot_id)

    def build_rows(self) -> dict[str, Any]:
        events = self.decisions.list_all_decisions()
        by_pair: dict[tuple[uuid.UUID, uuid.UUID], list[RecruiterDecision]] = defaultdict(list)
        for event in events:
            by_pair[(event.candidate_id, event.job_id)].append(event)
        rows: list[dict[str, Any]] = []
        exclusions: dict[str, int] = defaultdict(int)
        schemas: set[str] = set()
        ontologies: set[str] = set()
        embeddings: set[str] = set()
        times: list[datetime] = []
        for pair in self.decisions.scored_pairs():
            if pair not in by_pair:
                exclusions["no_decision"] += 1
        for (_cid, _jid), history in by_pair.items():
            binary = [item for item in history if item.action in BINARY_ACTIONS]
            if not binary:
                if history:
                    exclusions[_exclusion_for_non_binary(history[-1].action)] += 1
                else:
                    exclusions["no_decision"] += 1
                continue
            chosen = binary[-1]
            times.append(chosen.created_at)
            snapshot, reason = self._resolve_snapshot(chosen)
            if snapshot is None:
                exclusions[reason or "missing_feature_snapshot"] += 1
                continue
            eligible, exclude_reason, payload = _row_from_snapshot(chosen, snapshot, history)
            if not eligible or payload is None:
                exclusions[exclude_reason or "invalid_feature_values"] += 1
                continue
            rows.append(payload)
            schemas.add(payload["feature_schema_version"])
            if payload.get("ontology_version"):
                ontologies.add(str(payload["ontology_version"]))
            emb = payload.get("embedding_model_name")
            if emb:
                embeddings.add(
                    f"{emb}|{payload.get('embedding_model_version')}|{payload.get('embedding_text_version')}"
                )
        positives = sum(1 for item in rows if item["label"] == 1)
        negatives = sum(1 for item in rows if item["label"] == 0)
        total = len(rows)
        return {
            "rows": rows,
            "positive_count": positives,
            "negative_count": negatives,
            "positive_ratio": (positives / total) if total else 0.0,
            "negative_ratio": (negatives / total) if total else 0.0,
            "excluded_count": int(sum(exclusions.values())),
            "exclusion_reasons": dict(exclusions),
            "feature_schema_versions": sorted(schemas),
            "ontology_versions": sorted(ontologies),
            "embedding_versions": sorted(embeddings),
            "source_decision_range": {
                "min": min(times).isoformat() if times else None,
                "max": max(times).isoformat() if times else None,
            },
        }

    def _resolve_snapshot(
        self, decision: RecruiterDecision
    ) -> tuple[FeatureSnapshot | None, str | None]:
        if decision.feature_snapshot_id is not None:
            stored = self.decisions.get_snapshot(decision.feature_snapshot_id)
            if stored is None:
                return None, "missing_feature_snapshot"
            if stored.created_at > decision.created_at:
                return None, "feature_snapshot_after_decision"
            return stored, None
        found = self.decisions.snapshot_at_or_before(
            candidate_id=decision.candidate_id,
            job_id=decision.job_id,
            when=decision.created_at,
        )
        if found is None:
            return None, "missing_feature_snapshot"
        return found, None


def _exclusion_for_non_binary(action: str) -> str:
    if action == "review":
        return "review_unlabeled"
    if action in {"view", "compare", "hire"}:
        return "unsupported_action"
    return "no_decision"


def _row_from_snapshot(
    decision: RecruiterDecision,
    snapshot: FeatureSnapshot,
    history: list[RecruiterDecision],
) -> tuple[bool, str | None, dict[str, Any] | None]:
    if snapshot.created_at > decision.created_at:
        return False, "feature_snapshot_after_decision", None
    schema = snapshot.feature_schema_version
    if schema not in SUPPORTED_FEATURE_SCHEMAS:
        return False, "invalid_schema", None
    raw = dict(snapshot.features or {})
    ontology = raw.get("ontology_version")
    run = snapshot.match_run
    if not ontology and run is not None and run.ontology_version is not None:
        ontology = run.ontology_version.version
    if not ontology:
        return False, "unknown_ontology_version", None
    if not _valid_feature_values(raw):
        return False, "invalid_feature_values", None
    semantic_on = bool(raw.get("semantic_similarity_available"))
    if semantic_on and not raw.get("embedding_model_name"):
        return False, "unknown_embedding_identity", None
    features = _sanitize_features(raw)
    if "label" in features:
        return False, "label_in_features", None
    binary_history = [item for item in history if item.action in BINARY_ACTIONS]
    recruiters = {item.recruiter_id for item in binary_history}
    actions = {item.action for item in binary_history}
    conflict = len(recruiters) > 1 and len(actions) > 1
    label = 1 if decision.action == BINARY_POSITIVE else 0
    if decision.action == BINARY_NEGATIVE:
        label = 0
    payload = {
        "candidate_id": str(decision.candidate_id),
        "job_id": str(decision.job_id),
        "label": label,
        "decision_id": str(decision.id),
        "decision_time": decision.created_at.isoformat(),
        "match_run_id": str(snapshot.match_run_id),
        "feature_snapshot_id": str(snapshot.id),
        "feature_schema_version": schema,
        "ontology_version": ontology,
        "embedding_model_name": raw.get("embedding_model_name"),
        "embedding_model_version": raw.get("embedding_model_version"),
        "embedding_dimensions": raw.get("embedding_dimensions"),
        "embedding_text_version": raw.get("embedding_text_version"),
        "decision_conflict": conflict,
        "grouping": {"job_id": str(decision.job_id)},
        "features": features,
    }
    return True, None, payload


def _sanitize_features(raw: dict[str, Any]) -> dict[str, Any]:
    blocked = LEAKAGE_KEYS | PROTECTED_KEYS | GROUPING_KEYS
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        lowered = key.lower()
        if lowered in blocked or key in blocked:
            continue
        if lowered in {"resume_text", "note", "password", "token"}:
            continue
        cleaned[key] = value
    return cleaned


def _valid_feature_values(raw: dict[str, Any]) -> bool:
    match = raw.get("current_match")
    if match is None:
        return False
    try:
        number = float(match)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(number) or number < 0 or number > 1:
        return False
    potential = raw.get("potential")
    if potential is not None:
        try:
            number = float(potential)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(number) or number < 0 or number > 1:
            return False
    return True


def _checksum(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
