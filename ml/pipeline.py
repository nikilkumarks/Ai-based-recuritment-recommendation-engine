"""Offline shortlist-model training. Read-only against dataset snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from xgboost import XGBClassifier

from app.modules.features.schema import (
    ML_FEATURE_SCHEMA_VERSION,
    ML_PREPROCESS_VERSION,
    ordered_feature_names,
)
from ml.artifacts import save_artifact
from ml.baselines import column_scores, random_probabilities
from ml.metrics import evaluate_scores, metric_value
from ml.split import group_folds
from ml.validate import INSUFFICIENT_MESSAGE, validate_dataset

SKIPPED = "skipped_insufficient_data"


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    min_rows: int,
    min_positives: int,
    min_negatives: int,
    min_jobs: int,
    cv_folds: int,
    seed: int,
    xgb_params: dict[str, Any],
    primary_metric: str,
    test_fixture_only: bool = False,
) -> dict[str, Any]:
    """Group-aware evaluation. Does not write artifacts or mutate source rows."""
    report = validate_dataset(
        rows,
        min_rows=min_rows,
        min_positives=min_positives,
        min_negatives=min_negatives,
        min_jobs=min_jobs,
        allow_insufficient=False,
    )
    if report["leakage"]:
        return {
            "status": "failed_leakage",
            "message": "Training failed: leakage detected.",
            "validation": _public_validation(report),
            "metrics": None,
            "X": None,
            "y": None,
        }
    if not report["eligible"]:
        return {
            "status": SKIPPED,
            "message": INSUFFICIENT_MESSAGE,
            "validation": _public_validation(report),
            "metrics": None,
            "X": None,
            "y": None,
        }
    X = np.asarray(report["X"], dtype=float)
    y = np.asarray(report["y"], dtype=int)
    groups = list(report["groups"])
    split = group_folds(groups, cv_folds)
    if isinstance(split, str):
        return {
            "status": SKIPPED,
            "message": INSUFFICIENT_MESSAGE,
            "validation": {**_public_validation(report), "reasons": report["reasons"] + [split]},
            "metrics": None,
            "X": None,
            "y": None,
        }
    n_folds, folds = split
    oof = {
        "random": np.zeros(len(y), dtype=float),
        "skill_overlap": np.zeros(len(y), dtype=float),
        "baseline": np.zeros(len(y), dtype=float),
        "xgboost": np.zeros(len(y), dtype=float),
    }
    for fold_i, (train_idx, test_idx) in enumerate(folds):
        X_train, y_train = X[train_idx], y[train_idx]
        prior = float(np.mean(y_train)) if y_train.size else 0.5
        n_pos = max(int(np.sum(y_train)), 1)
        n_neg = max(int(y_train.size - np.sum(y_train)), 1)
        params = dict(xgb_params)
        params["scale_pos_weight"] = n_neg / n_pos
        params["random_state"] = seed
        model = _fit(X_train, y_train, params)
        oof["random"][test_idx] = random_probabilities(len(test_idx), seed + fold_i, prior)
        oof["skill_overlap"][test_idx] = column_scores(X[test_idx], "required_skill_coverage")
        oof["baseline"][test_idx] = column_scores(X[test_idx], "current_match")
        oof["xgboost"][test_idx] = model.predict_proba(X[test_idx])[:, 1]
    metrics = {
        "random": evaluate_scores(y, oof["random"], groups),
        "skill_overlap": evaluate_scores(y, oof["skill_overlap"], groups),
        "baseline": evaluate_scores(y, oof["baseline"], groups),
        "xgboost": evaluate_scores(y, oof["xgboost"], groups),
    }
    return {
        "status": "evaluated",
        "message": "Evaluation complete. Metrics are not hiring outcomes.",
        "validation": _public_validation(report),
        "metrics": metrics,
        "cv_folds": n_folds,
        "X": X,
        "y": y,
        "groups": groups,
        "feature_names": ordered_feature_names(),
        "activation": activation_eligibility(metrics, primary_metric, test_fixture_only),
        "ontology_versions": report["ontology_versions"],
        "feature_schema_versions": report["feature_schema_versions"],
        "class_balance": {
            "positive_count": report["positive_count"],
            "negative_count": report["negative_count"],
            "positive_ratio": report["positive_ratio"],
            "negative_ratio": report["negative_ratio"],
        },
        "leakage_checks": report["leakage"],
    }


def train(
    rows: list[dict[str, Any]],
    *,
    dataset_id: str | None,
    artifact_root: Path,
    min_rows: int,
    min_positives: int,
    min_negatives: int,
    min_jobs: int,
    cv_folds: int,
    seed: int,
    xgb_params: dict[str, Any],
    primary_metric: str,
    test_fixture_only: bool = False,
) -> dict[str, Any]:
    """Train XGBoost or skip. Never fabricates labels or overwrites source rows."""
    evaluated = evaluate_rows(
        rows,
        min_rows=min_rows,
        min_positives=min_positives,
        min_negatives=min_negatives,
        min_jobs=min_jobs,
        cv_folds=cv_folds,
        seed=seed,
        xgb_params=xgb_params,
        primary_metric=primary_metric,
        test_fixture_only=test_fixture_only,
    )
    if evaluated["status"] != "evaluated":
        return {
            **evaluated,
            "artifact_dir": None,
            "model_version": None,
        }
    X = evaluated["X"]
    y = evaluated["y"]
    n_neg = max(int(len(y) - int(y.sum())), 1)
    n_pos = max(int(y.sum()), 1)
    final = _fit(
        X,
        y,
        {**xgb_params, "scale_pos_weight": n_neg / n_pos, "random_state": seed},
    )
    feature_names = list(evaluated["feature_names"])
    checksum = hashlib.sha256(json.dumps(y.tolist()).encode()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "test-fixture-only-" if test_fixture_only else ""
    version = f"{prefix}xgb-shortlist-v1-{stamp}-{checksum}"
    metadata = {
        "model_version": version,
        "algorithm": "xgboost.XGBClassifier",
        "target": "recruiter_shortlist",
        "target_note": (
            "Predicts recruiter shortlist behavior. Not hiring, job performance, "
            "future success, candidate quality, or guaranteed selection."
        ),
        "dataset_snapshot_id": dataset_id,
        "feature_schema_version": ML_FEATURE_SCHEMA_VERSION,
        "snapshot_feature_schemas": evaluated["feature_schema_versions"],
        "preprocessing_version": ML_PREPROCESS_VERSION,
        "feature_names": feature_names,
        "ontology_versions": evaluated["ontology_versions"],
        "embedding_identity": _embedding_identity(rows),
        "random_seed": seed,
        "cv_folds": evaluated["cv_folds"],
        "xgb_params": xgb_params,
        "metrics": evaluated["metrics"],
        "class_balance": evaluated["class_balance"],
        "leakage_checks": evaluated["leakage_checks"],
        "library_versions": _library_versions(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "test_fixture_only": test_fixture_only,
        "fixture_warning": "TEST FIXTURE ONLY" if test_fixture_only else None,
        "primary_metric": primary_metric,
        "activation": evaluated["activation"],
    }
    path = save_artifact(root=artifact_root, version=version, model=final, metadata=metadata)
    return {
        "status": "trained_candidate",
        "message": "Candidate model trained. Not activated.",
        "validation": evaluated["validation"],
        "artifact_dir": str(path),
        "model_version": version,
        "metrics": evaluated["metrics"],
        "activation": metadata["activation"],
        "test_fixture_only": test_fixture_only,
        "cv_folds": evaluated["cv_folds"],
        "feature_names": feature_names,
        "metadata": metadata,
    }


def activation_eligibility(
    metrics: dict[str, Any], primary_metric: str, test_fixture_only: bool
) -> dict[str, Any]:
    xgb = metric_value(metrics.get("xgboost") or {}, primary_metric)
    baseline = metric_value(metrics.get("baseline") or {}, primary_metric)
    xgb_auc = metric_value(metrics.get("xgboost") or {}, "roc_auc")
    base_auc = metric_value(metrics.get("baseline") or {}, "roc_auc")
    reasons: list[str] = []
    if xgb is None or baseline is None:
        fallback = "roc_auc"
        xgb = metric_value(metrics.get("xgboost") or {}, fallback)
        baseline = metric_value(metrics.get("baseline") or {}, fallback)
        if xgb is None or baseline is None:
            reasons.append("evaluation_metrics_unavailable")
    if xgb is not None and baseline is not None and xgb <= baseline:
        reasons.append("does_not_beat_deterministic_baseline")
    if xgb_auc is not None and base_auc is not None and xgb_auc < base_auc - 0.10:
        reasons.append("severe_roc_auc_regression")
    eligible = not reasons
    return {
        "eligible": eligible,
        "reasons": reasons,
        "primary_metric": primary_metric,
        "test_fixture_only": test_fixture_only,
        "note": (
            "TEST FIXTURE ONLY. Not project performance."
            if test_fixture_only
            else "Activation requires a documented review. Never automatic."
        ),
    }


def _fit(X: np.ndarray, y: np.ndarray, params: dict[str, Any]) -> XGBClassifier:
    model = XGBClassifier(
        n_estimators=int(params.get("n_estimators", 80)),
        max_depth=int(params.get("max_depth", 3)),
        learning_rate=float(params.get("learning_rate", 0.1)),
        subsample=float(params.get("subsample", 0.8)),
        colsample_bytree=float(params.get("colsample_bytree", 0.8)),
        min_child_weight=int(params.get("min_child_weight", 1)),
        reg_lambda=float(params.get("reg_lambda", 1.0)),
        objective="binary:logistic",
        eval_metric="logloss",
        n_jobs=1,
        verbosity=0,
        random_state=int(params.get("random_state", 42)),
        scale_pos_weight=float(params.get("scale_pos_weight", 1.0)),
    )
    model.fit(X, y)
    return model


def _public_validation(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_count": report["row_count"],
        "positive_count": report["positive_count"],
        "negative_count": report["negative_count"],
        "positive_ratio": report["positive_ratio"],
        "negative_ratio": report["negative_ratio"],
        "unique_jobs": report["unique_jobs"],
        "reasons": report["reasons"],
        "excluded": report["excluded"],
        "leakage": report["leakage"],
        "feature_schema_versions": report["feature_schema_versions"],
        "ontology_versions": report["ontology_versions"],
    }


def _library_versions() -> dict[str, str]:
    import sys

    import sklearn
    import xgboost

    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "sklearn": sklearn.__version__,
        "xgboost": xgboost.__version__,
    }


def _embedding_identity(rows: list[dict[str, Any]]) -> list[str]:
    values: set[str] = set()
    for row in rows:
        name = row.get("embedding_model_name")
        if name:
            values.add(
                f"{name}|{row.get('embedding_model_version')}|{row.get('embedding_text_version')}"
            )
    return sorted(values)
