"""Model registry mutations. Never auto-activate. No FastAPI imports."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.models import MlModel
from app.models.enums import MlModelStatus
from app.modules.features.runtime import artifact_root, reset_model_cache
from app.modules.identity import audit

MODEL_ACTIVATED = "ml_model_activated"
MODEL_REJECTED = "ml_model_rejected"


def list_models(db: Session) -> list[MlModel]:
    return list(db.scalars(select(MlModel).order_by(MlModel.created_at.desc())).all())


def get_model(db: Session, model_id: uuid.UUID) -> MlModel | None:
    return db.get(MlModel, model_id)


def public_model_payload(row: MlModel) -> dict[str, Any]:
    metrics = dict(row.metrics or {})
    evaluation = metrics.get("evaluation") or metrics.get("metrics")
    activation = metrics.get("activation") or {}
    fixture = bool(metrics.get("test_fixture_only"))
    return {
        "id": str(row.id),
        "version": row.version,
        "algorithm": row.model_type,
        "status": row.status,
        "feature_schema_version": row.feature_schema_version,
        "dataset_snapshot_id": metrics.get("dataset_snapshot_id"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
        "evaluation": evaluation,
        "baseline_comparison": _baseline_comparison(evaluation if isinstance(evaluation, dict) else {}),
        "activation": activation,
        "class_balance": metrics.get("class_balance"),
        "leakage_checks": metrics.get("leakage_checks"),
        "cv_folds": metrics.get("cv_folds"),
        "random_seed": metrics.get("random_seed"),
        "test_fixture_only": fixture,
        "warning": "TEST FIXTURE ONLY. Not project performance." if fixture else None,
        "target_note": (
            "Recruiter shortlist/reject decisions are behavioral labels and are not "
            "ground-truth hiring outcomes."
        ),
    }


def activate_model(db: Session, *, actor_id: uuid.UUID, model_id: uuid.UUID) -> MlModel:
    row = db.get(MlModel, model_id)
    if row is None:
        raise NotFoundError("Model not found.")
    if row.status == MlModelStatus.REJECTED.value:
        raise ConflictError("Rejected models cannot be activated.")
    if row.status == MlModelStatus.ACTIVE.value:
        return row
    reasons = activation_blockers(row)
    if reasons:
        raise ConflictError("Model is not eligible for activation: " + "; ".join(reasons))
    now = datetime.now(timezone.utc)
    current_active = db.scalars(
        select(MlModel).where(MlModel.status == MlModelStatus.ACTIVE.value)
    ).all()
    for active in current_active:
        if active.id != row.id:
            active.status = MlModelStatus.RETIRED.value
    row.status = MlModelStatus.ACTIVE.value
    row.activated_at = now
    db.flush()
    reset_model_cache()
    audit.record_audit(
        db,
        action=MODEL_ACTIVATED,
        resource_type="ml_model",
        actor_user_id=actor_id,
        resource_id=row.id,
        metadata={"version": row.version, "previous_active": [str(item.id) for item in current_active]},
    )
    db.flush()
    return row


def reject_model(db: Session, *, actor_id: uuid.UUID, model_id: uuid.UUID) -> MlModel:
    row = db.get(MlModel, model_id)
    if row is None:
        raise NotFoundError("Model not found.")
    if row.status == MlModelStatus.ACTIVE.value:
        raise ConflictError("Deactivate by activating another eligible model, or retire via policy.")
    if row.status == MlModelStatus.REJECTED.value:
        return row
    row.status = MlModelStatus.REJECTED.value
    db.flush()
    audit.record_audit(
        db,
        action=MODEL_REJECTED,
        resource_type="ml_model",
        actor_user_id=actor_id,
        resource_id=row.id,
        metadata={"version": row.version},
    )
    db.flush()
    return row


def activation_blockers(row: MlModel) -> list[str]:
    settings = get_settings()
    reasons: list[str] = []
    metrics = dict(row.metrics or {})
    if metrics.get("test_fixture_only") and settings.is_production():
        reasons.append("test_fixture_only")
    activation = metrics.get("activation") if isinstance(metrics.get("activation"), dict) else {}
    if not activation.get("eligible"):
        reasons.append("activation_policy_failed")
        reasons.extend(list(activation.get("reasons") or []))
    evaluation = metrics.get("evaluation") or metrics.get("metrics")
    if not evaluation:
        reasons.append("evaluation_missing")
    directory = artifact_root() / (row.artifact_uri or row.version)
    if not (directory / "model.json").is_file() or not (directory / "metadata.json").is_file():
        reasons.append("artifact_missing")
    else:
        try:
            import json

            metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        except Exception:
            reasons.append("artifact_corrupt")
            metadata = {}
        if metadata.get("feature_schema_version") != row.feature_schema_version:
            reasons.append("schema_mismatch")
        if metadata.get("leakage_checks"):
            reasons.append("leakage_detected")
    return list(dict.fromkeys(reasons))


def _baseline_comparison(evaluation: dict[str, Any]) -> dict[str, Any]:
    if not evaluation:
        return {}
    return {
        "random": evaluation.get("random"),
        "skill_overlap": evaluation.get("skill_overlap"),
        "baseline": evaluation.get("baseline"),
        "xgboost": evaluation.get("xgboost"),
    }
