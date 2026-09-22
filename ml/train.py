"""Offline training CLI. Does not expose HTTP. Does not fabricate labels."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INSUFFICIENT_FROM_RESULT = "Insufficient real labeled data for training experiment."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Train an XGBoost shortlist model from a dataset snapshot. "
            "Predicts recruiter shortlist behavior, not hiring."
        )
    )
    parser.add_argument("--dataset", help="dataset_snapshot_id")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Write a candidate registry row when training succeeds.",
    )
    args = parser.parse_args(argv)
    from app.core.config import get_settings
    from app.core.db import SessionLocal
    from ml.data import load_snapshot, snapshot_rows
    from ml.pipeline import SKIPPED, train
    from ml.registry import record_candidate, record_skipped_run

    settings = get_settings()
    artifacts = Path(settings.model_artifact_dir)
    if not artifacts.is_absolute():
        artifacts = (ROOT / artifacts).resolve()
    params = {
        "n_estimators": settings.xgb_n_estimators,
        "max_depth": settings.xgb_max_depth,
        "learning_rate": settings.xgb_learning_rate,
        "subsample": settings.xgb_subsample,
        "colsample_bytree": settings.xgb_colsample_bytree,
        "min_child_weight": settings.xgb_min_child_weight,
        "reg_lambda": settings.xgb_reg_lambda,
    }
    if not args.dataset:
        print("Training skipped:")
        print("insufficient real labeled data.")
        print(INSUFFICIENT_FROM_RESULT)
        return 2
    db = SessionLocal()
    try:
        snapshot = load_snapshot(db, uuid.UUID(args.dataset))
        if snapshot is None:
            print("Dataset snapshot not found.")
            return 2
        rows_before = json.dumps(snapshot.rows, sort_keys=True, default=str)
        result = train(
            snapshot_rows(snapshot),
            dataset_id=str(snapshot.id),
            artifact_root=artifacts,
            min_rows=settings.min_training_rows,
            min_positives=settings.min_positive_labels,
            min_negatives=settings.min_negative_labels,
            min_jobs=settings.min_unique_jobs,
            cv_folds=settings.ml_cv_folds,
            seed=settings.ml_random_seed,
            xgb_params=params,
            primary_metric=settings.ml_primary_metric,
            test_fixture_only=False,
        )
        rows_after = json.dumps(snapshot.rows, sort_keys=True, default=str)
        if rows_before != rows_after:
            raise RuntimeError("Training mutated the dataset snapshot.")
        if result["status"] == SKIPPED:
            print("Training skipped:")
            print("insufficient real labeled data.")
            print(INSUFFICIENT_FROM_RESULT)
            for reason in (result.get("validation") or {}).get("reasons") or []:
                print(f"- {reason}")
            if args.register:
                record_skipped_run(
                    db,
                    dataset_id=snapshot.id,
                    reason=result.get("validation") or {},
                )
                db.commit()
            return 0
        if result["status"] != "trained_candidate":
            print(result.get("message") or result["status"])
            return 1
        print(f"Candidate model: {result['model_version']}")
        print("Not activated. Recruiter shortlist labels are not hiring outcomes.")
        if result.get("test_fixture_only"):
            print("TEST FIXTURE ONLY. Not project performance.")
        if args.register:
            record_candidate(
                db,
                dataset_id=snapshot.id,
                version=result["model_version"],
                artifact_uri=result["model_version"],
                metadata=result["metadata"],
                test_fixture_only=False,
            )
            db.commit()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
