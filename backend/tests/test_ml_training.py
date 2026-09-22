"""Phase 10 training pipeline. TEST FIXTURE ONLY rows are never project metrics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.modules.features.schema import FORBIDDEN_FEATURE_KEYS, ordered_feature_names, vectorize_features
from ml.artifacts import load_artifact
from ml.baselines import column_scores, random_probabilities
from ml.fixture import FIXTURE_MARK, fixture_rows
from ml.leakage import leakage_errors
from ml.metrics import UNAVAILABLE, evaluate_scores
from ml.pipeline import SKIPPED, evaluate_rows, train
from ml.split import group_folds
from ml.train import INSUFFICIENT_FROM_RESULT
from ml.train import main as train_main
from ml.validate import INSUFFICIENT_MESSAGE, validate_dataset

XGB_PARAMS = {
    "n_estimators": 24,
    "max_depth": 2,
    "learning_rate": 0.2,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "min_child_weight": 1,
    "reg_lambda": 1.0,
}

TRAIN_KW = dict(
    min_rows=50,
    min_positives=5,
    min_negatives=5,
    min_jobs=2,
    cv_folds=5,
    seed=42,
    xgb_params=XGB_PARAMS,
    primary_metric="ndcg_at_5",
)


def _tiny_rows(*, n=3, positives=2, jobs=1, extra_features=None):
    rows = []
    remaining_pos = positives
    for i in range(n):
        label = 1 if remaining_pos > 0 else 0
        remaining_pos -= label
        features = {
            "required_skill_coverage": 0.8 if label else 0.1,
            "current_match": 0.7 if label else 0.2,
            "semantic_similarity_available": False,
        }
        if extra_features:
            features.update(extra_features)
        rows.append(
            {
                "candidate_id": f"c-{i}",
                "job_id": f"j-{i % jobs}",
                "label": label,
                "decision_time": "2026-01-02T00:00:00+00:00",
                "feature_schema_version": "feature-schema-v2",
                "ontology_version": "seed-0.1",
                "grouping": {"job_id": f"j-{i % jobs}"},
                "features": features,
            }
        )
    return rows


def test_insufficient_dataset_blocks_training(tmp_path: Path) -> None:
    rows = _tiny_rows(n=3, positives=2, jobs=1)
    result = train(rows, dataset_id="real-small", artifact_root=tmp_path, test_fixture_only=False, **TRAIN_KW)
    assert result["status"] == SKIPPED
    assert result["message"] == INSUFFICIENT_MESSAGE
    assert result["artifact_dir"] is None
    assert list(tmp_path.iterdir()) == []
    assert result["metrics"] is None


def test_cli_skips_three_row_dataset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    code = train_main([])
    assert code == 2


def test_insufficient_positive_labels_block_training(tmp_path: Path) -> None:
    rows = fixture_rows()
    for row in rows:
        row["label"] = 0
    result = train(rows, dataset_id=None, artifact_root=tmp_path, **TRAIN_KW)
    assert result["status"] == SKIPPED
    assert any("min_positive_labels" in item for item in result["validation"]["reasons"])
    assert list(tmp_path.iterdir()) == []


def test_insufficient_negative_labels_block_training(tmp_path: Path) -> None:
    rows = fixture_rows()
    for row in rows:
        row["label"] = 1
    result = train(rows, dataset_id=None, artifact_root=tmp_path, **TRAIN_KW)
    assert result["status"] == SKIPPED
    assert any("min_negative_labels" in item for item in result["validation"]["reasons"])


def test_insufficient_unique_jobs_block_groupkfold() -> None:
    groups = ["job-a"] * 60
    assert group_folds(groups, 5) == "insufficient_unique_jobs_for_groupkfold"


def test_groupkfold_has_no_job_leakage() -> None:
    groups = [f"job-{i // 10}" for i in range(60)]
    split = group_folds(groups, 5)
    assert not isinstance(split, str)
    n_folds, folds = split
    assert n_folds == 5
    for train_idx, test_idx in folds:
        train_g = {groups[i] for i in train_idx}
        test_g = {groups[i] for i in test_idx}
        assert not (train_g & test_g)


def test_forbidden_features_rejected() -> None:
    names = ordered_feature_names()
    assert not ({name.lower() for name in names} & {key.lower() for key in FORBIDDEN_FEATURE_KEYS})
    rows = fixture_rows()[:3]
    rows[0]["features"]["gender"] = "x"
    errors = leakage_errors(rows)
    assert any("forbidden_key" in item for item in errors)
    result = validate_dataset(rows, min_rows=1, min_positives=0, min_negatives=0, min_jobs=1)
    assert result["eligible"] is False


def test_ids_and_labels_not_in_feature_vector() -> None:
    names = ordered_feature_names()
    for banned in ("candidate_id", "job_id", "label", "reason", "note", "decision_note"):
        assert banned not in names
        assert banned not in {item.lower() for item in names}


def test_protected_attributes_rejected() -> None:
    rows = _tiny_rows(n=3, extra_features={"religion": "x", "college_prestige": 1})
    assert leakage_errors(rows)


def test_feature_schema_mismatch_rejected() -> None:
    rows = fixture_rows()[:5]
    for row in rows:
        row["feature_schema_version"] = "feature-schema-v99"
    report = validate_dataset(rows, min_rows=1, min_positives=0, min_negatives=0, min_jobs=1)
    assert report["row_count"] == 0
    assert report["excluded"]["invalid_schema"] == 5


def test_missing_and_invalid_feature_values() -> None:
    ok, err = vectorize_features({"required_skill_coverage": 0.5})
    assert err == "missing_required_feature:current_match"
    ok, err = vectorize_features({"required_skill_coverage": 0.5, "current_match": float("inf")})
    assert err == "invalid_feature_value:current_match"
    vector, err = vectorize_features(
        {"required_skill_coverage": 0.4, "current_match": 0.2, "candidate_experience_years": None}
    )
    assert err is None
    names = ordered_feature_names()
    years_idx = names.index("candidate_experience_years")
    missing_idx = names.index("candidate_experience_years__missing")
    assert vector[years_idx] == -1.0
    assert vector[missing_idx] == 1.0


def test_random_baseline_reproducible() -> None:
    a = random_probabilities(8, 42, 0.4)
    b = random_probabilities(8, 42, 0.4)
    c = random_probabilities(8, 7, 0.4)
    assert np.allclose(a, b)
    assert not np.allclose(a, c)


def test_exact_skill_and_deterministic_baselines() -> None:
    rows = fixture_rows()
    report = validate_dataset(rows, min_rows=50, min_positives=5, min_negatives=5, min_jobs=2)
    X = np.asarray(report["X"])
    coverage = column_scores(X, "required_skill_coverage")
    current = column_scores(X, "current_match")
    assert coverage.min() >= 0
    assert current.max() <= 1


def test_xgboost_fixture_train_predict_and_artifact(tmp_path: Path) -> None:
    rows = fixture_rows()
    copied = json.loads(json.dumps(rows))
    result = train(
        rows,
        dataset_id="fixture",
        artifact_root=tmp_path,
        test_fixture_only=True,
        **TRAIN_KW,
    )
    assert result["status"] == "trained_candidate"
    assert result["test_fixture_only"] is True
    assert FIXTURE_MARK in (result["metadata"]["fixture_warning"] or "")
    assert result["model_version"].startswith("test-fixture-only-xgb-shortlist-v1")
    model, metadata = load_artifact(Path(result["artifact_dir"]))
    vector, error = vectorize_features(rows[0]["features"])
    assert error is None
    proba = model.predict_proba([vector])
    assert proba.shape == (1, 2)
    assert copied == rows
    assert metadata["random_seed"] == 42
    assert metadata["feature_schema_version"] == "ml-feature-schema-v1"
    assert "candidate_id" not in metadata["feature_names"]
    second = train(
        rows,
        dataset_id="fixture",
        artifact_root=tmp_path / "b",
        test_fixture_only=True,
        **TRAIN_KW,
    )
    assert np.allclose(
        model.predict_proba([vector]),
        load_artifact(Path(second["artifact_dir"]))[0].predict_proba([vector]),
        atol=1e-6,
    )


def test_evaluation_unavailable_metrics_when_insufficient() -> None:
    metrics = evaluate_scores([1, 1, 1], [0.2, 0.3, 0.4], ["a", "a", "a"])
    assert metrics["roc_auc"] == UNAVAILABLE
    result = evaluate_rows(_tiny_rows(), **TRAIN_KW)
    assert result["status"] == SKIPPED
    assert result["metrics"] is None


def test_dataset_snapshot_immutability(db_session: Session) -> None:
    from app.models import DatasetSnapshot, RecruiterDecision

    before_decisions = db_session.query(RecruiterDecision).count()
    before_snapshots = db_session.query(DatasetSnapshot).count()
    rows = _tiny_rows()
    payload = json.dumps(rows)
    train(rows, dataset_id=None, artifact_root=Path("unused"), **TRAIN_KW)
    assert json.dumps(rows) == payload
    assert db_session.query(RecruiterDecision).count() == before_decisions
    assert db_session.query(DatasetSnapshot).count() == before_snapshots


def test_insufficient_message_constant() -> None:
    assert INSUFFICIENT_FROM_RESULT == INSUFFICIENT_MESSAGE
