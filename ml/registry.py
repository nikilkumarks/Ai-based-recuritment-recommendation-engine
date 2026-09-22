"""Write candidate models. Never auto-activate. Training is read-only on source tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import MlModel, MlTrainingRun
from app.models.enums import MlModelStatus, TrainingRunStatus


def record_skipped_run(
    db: Session,
    *,
    dataset_id: uuid.UUID | None,
    reason: dict[str, Any],
) -> MlTrainingRun:
    row = MlTrainingRun(
        dataset_snapshot_id=dataset_id,
        model_type="xgboost",
        parameters={"skipped": True},
        metrics=reason,
        feature_schema_version="ml-feature-schema-v1",
        status=TrainingRunStatus.FAILED.value,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def record_candidate(
    db: Session,
    *,
    dataset_id: uuid.UUID | None,
    version: str,
    artifact_uri: str,
    metadata: dict[str, Any],
    test_fixture_only: bool,
) -> tuple[MlTrainingRun, MlModel]:
    started = datetime.now(timezone.utc)
    run = MlTrainingRun(
        dataset_snapshot_id=dataset_id,
        model_type="xgboost",
        parameters={
            "xgb_params": metadata.get("xgb_params"),
            "random_seed": metadata.get("random_seed"),
            "test_fixture_only": test_fixture_only,
        },
        metrics=metadata.get("metrics"),
        feature_schema_version=metadata.get("feature_schema_version"),
        embedding_model=(metadata.get("embedding_identity") or [None])[0],
        status=TrainingRunStatus.COMPLETED.value,
        started_at=started,
        finished_at=datetime.now(timezone.utc),
        git_sha=None,
    )
    db.add(run)
    db.flush()
    model = MlModel(
        version=version,
        model_type="xgboost",
        artifact_uri=artifact_uri,
        feature_schema_version=str(metadata.get("feature_schema_version")),
        embedding_model=run.embedding_model,
        training_run_id=run.id,
        metrics={
            "evaluation": metadata.get("metrics"),
            "activation": metadata.get("activation"),
            "class_balance": metadata.get("class_balance"),
            "leakage_checks": metadata.get("leakage_checks"),
            "cv_folds": metadata.get("cv_folds"),
            "test_fixture_only": test_fixture_only,
            "dataset_snapshot_id": str(dataset_id) if dataset_id else None,
            "random_seed": metadata.get("random_seed"),
            "feature_names": metadata.get("feature_names"),
            "preprocessing_version": metadata.get("preprocessing_version"),
            "target": metadata.get("target"),
        },
        parameters=metadata.get("xgb_params"),
        checksum=None,
        status=MlModelStatus.CANDIDATE.value,
    )
    db.add(model)
    db.flush()
    return run, model
