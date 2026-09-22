"""Offline evaluation CLI. Compares baselines and XGBoost on one snapshot."""

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate shortlist models. Not hiring metrics.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--artifact", help="Artifact directory name under MODEL_ARTIFACT_DIR")
    args = parser.parse_args(argv)
    from app.core.config import get_settings
    from app.core.db import SessionLocal
    from ml.artifacts import load_artifact
    from ml.data import load_snapshot, snapshot_rows
    from ml.pipeline import evaluate_rows

    settings = get_settings()
    db = SessionLocal()
    try:
        snapshot = load_snapshot(db, uuid.UUID(args.dataset))
        if snapshot is None:
            print("Dataset snapshot not found.")
            return 2
        rows = snapshot_rows(snapshot)
        if args.artifact:
            root = Path(settings.model_artifact_dir)
            if not root.is_absolute():
                root = ROOT / root
            _model, metadata = load_artifact((root / args.artifact).resolve())
            print(json.dumps(metadata.get("metrics") or {}, indent=2, default=str))
            if metadata.get("test_fixture_only"):
                print("TEST FIXTURE ONLY. Not project performance.")
            return 0
        result = evaluate_rows(
            rows,
            min_rows=settings.min_training_rows,
            min_positives=settings.min_positive_labels,
            min_negatives=settings.min_negative_labels,
            min_jobs=settings.min_unique_jobs,
            cv_folds=settings.ml_cv_folds,
            seed=settings.ml_random_seed,
            xgb_params={
                "n_estimators": settings.xgb_n_estimators,
                "max_depth": settings.xgb_max_depth,
                "learning_rate": settings.xgb_learning_rate,
                "subsample": settings.xgb_subsample,
                "colsample_bytree": settings.xgb_colsample_bytree,
                "min_child_weight": settings.xgb_min_child_weight,
                "reg_lambda": settings.xgb_reg_lambda,
            },
            primary_metric=settings.ml_primary_metric,
        )
        payload = {
            "status": result.get("status"),
            "message": result.get("message"),
            "validation": result.get("validation"),
            "metrics": result.get("metrics"),
            "activation": result.get("activation"),
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if result["status"] in {"evaluated", "skipped_insufficient_data"} else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
