"""Phase 10 registry, activation, and inference fallback. Fixture models are not project models."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import MlModel
from app.models.enums import MlModelStatus
from app.modules.features.runtime import reset_model_cache, score_features
from ml.fixture import fixture_rows
from ml.pipeline import train
from ml.registry import record_candidate
from tests.phase9_helpers import admin_token, bearer, recruiter_account
from tests.test_ml_training import TRAIN_KW

FIXTURE_NOTE = "TEST FIXTURE ONLY"


def _train_fixture(tmp_path: Path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "model_artifact_dir", str(tmp_path))
    reset_model_cache()
    return train(
        fixture_rows(),
        dataset_id="test-fixture-only",
        artifact_root=tmp_path,
        test_fixture_only=True,
        **TRAIN_KW,
    )


def _register(db_session: Session, result: dict, eligible: bool | None = None) -> MlModel:
    metadata = dict(result["metadata"])
    if eligible is not None:
        activation = dict(metadata.get("activation") or {})
        activation["eligible"] = eligible
        if eligible:
            activation["reasons"] = []
        else:
            activation.setdefault("reasons", ["does_not_beat_deterministic_baseline"])
        metadata["activation"] = activation
    suffix = ""
    if eligible is False:
        suffix = "-n"
    elif eligible is True:
        suffix = "-y"
    _run, model = record_candidate(
        db_session,
        dataset_id=None,
        version=result["model_version"] + suffix,
        artifact_uri=result["model_version"],
        metadata=metadata,
        test_fixture_only=True,
    )
    db_session.flush()
    return model


def test_no_public_training_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/train")
    assert response.status_code in {404, 405, 401}


def test_recruiter_cannot_activate_models(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch
) -> None:
    result = _train_fixture(tmp_path, monkeypatch)
    model = _register(db_session, result, eligible=True)
    rec_token, _ = recruiter_account(client, f"ml-rec-{uuid.uuid4().hex[:8]}@example.com", "Org")
    denied = client.post(f"/api/v1/admin/models/{model.id}/activate", headers=bearer(rec_token))
    assert denied.status_code == 403


def test_model_registry_candidate_activate_reject(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch
) -> None:
    result = _train_fixture(tmp_path, monkeypatch)
    first = _register(db_session, result, eligible=True)
    admin = admin_token(client, db_session, f"ml-admin-{uuid.uuid4().hex[:8]}@example.com")
    listed = client.get("/api/v1/admin/models", headers=bearer(admin))
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body[0]["test_fixture_only"] is True
    assert FIXTURE_NOTE in (body[0]["warning"] or "")
    assert "artifact_uri" not in body[0]
    assert "\\" not in json.dumps(body)
    assert "/ml/artifacts" not in json.dumps(body).replace("\\", "/")
    activated = client.post(f"/api/v1/admin/models/{first.id}/activate", headers=bearer(admin))
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    second_result = train(
        fixture_rows(),
        dataset_id="test-fixture-only",
        artifact_root=tmp_path,
        test_fixture_only=True,
        **TRAIN_KW,
    )
    payload = {**second_result, "model_version": second_result["model_version"] + "-b"}
    second = _register(db_session, payload, eligible=True)
    second.artifact_uri = result["model_version"]
    db_session.flush()
    again = client.post(f"/api/v1/admin/models/{second.id}/activate", headers=bearer(admin))
    assert again.status_code == 200, again.text
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.status == MlModelStatus.RETIRED.value
    assert second.status == MlModelStatus.ACTIVE.value
    assert db_session.query(MlModel).filter(MlModel.status == "active").count() == 1


def test_activation_policy_rejects_ineligible(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch
) -> None:
    result = _train_fixture(tmp_path, monkeypatch)
    model = _register(db_session, result, eligible=False)
    admin = admin_token(client, db_session, f"ml-pol-{uuid.uuid4().hex[:8]}@example.com")
    response = client.post(f"/api/v1/admin/models/{model.id}/activate", headers=bearer(admin))
    assert response.status_code == 409


def test_reject_policy(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch) -> None:
    result = _train_fixture(tmp_path, monkeypatch)
    model = _register(db_session, result, eligible=False)
    admin = admin_token(client, db_session, f"ml-rej-{uuid.uuid4().hex[:8]}@example.com")
    response = client.post(f"/api/v1/admin/models/{model.id}/reject", headers=bearer(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    activate = client.post(f"/api/v1/admin/models/{model.id}/activate", headers=bearer(admin))
    assert activate.status_code == 409


def test_inference_fallback_missing_corrupt_schema(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch, seeded_ontology
) -> None:
    result = _train_fixture(tmp_path, monkeypatch)
    model = _register(db_session, result, eligible=True)
    admin = admin_token(client, db_session, f"ml-inf-{uuid.uuid4().hex[:8]}@example.com")
    assert client.post(f"/api/v1/admin/models/{model.id}/activate", headers=bearer(admin)).status_code == 200
    features = fixture_rows()[0]["features"]
    scored = score_features(db_session, features, ontology_version="seed-0.1")
    assert scored.scoring_mode == "trained"
    assert scored.model_version == model.version
    assert scored.model_relevance_score is not None
    assert scored.ml_explanations
    assert scored.ml_explanations[0]["method"] in {"shap", "feature_importance"}

    (tmp_path / result["model_version"] / "model.json").write_text("not-a-model", encoding="utf-8")
    reset_model_cache()
    corrupt = score_features(db_session, features, ontology_version="seed-0.1")
    assert corrupt.scoring_mode == "baseline"
    assert corrupt.model_version is None
    assert corrupt.fallback_reason == "corrupt_artifact"

    (tmp_path / result["model_version"] / "model.json").unlink()
    reset_model_cache()
    missing = score_features(db_session, features, ontology_version="seed-0.1")
    assert missing.fallback_reason == "missing_artifact"

    meta_path = tmp_path / result["model_version"] / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["feature_schema_version"] = "ml-feature-schema-v99"
    # restore model file from a fresh train copy
    other = tmp_path / "restore"
    restored = train(fixture_rows(), dataset_id="x", artifact_root=other, test_fixture_only=True, **TRAIN_KW)
    model_src = Path(restored["artifact_dir"]) / "model.json"
    dest = tmp_path / result["model_version"]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "model.json").write_bytes(model_src.read_bytes())
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    reset_model_cache()
    mismatch = score_features(db_session, features, ontology_version="seed-0.1")
    assert mismatch.scoring_mode == "baseline"
    assert mismatch.fallback_reason == "feature_schema_mismatch"


def test_matching_uses_trained_score_and_falls_back(
    client: TestClient, db_session: Session, tmp_path: Path, monkeypatch, seeded_ontology
) -> None:
    from tests.phase9_helpers import job_with_scenario_skills, prepared_candidate

    result = _train_fixture(tmp_path, monkeypatch)
    model = _register(db_session, result, eligible=True)
    admin = admin_token(client, db_session, f"ml-match-{uuid.uuid4().hex[:8]}@example.com")
    assert client.post(f"/api/v1/admin/models/{model.id}/activate", headers=bearer(admin)).status_code == 200
    rec_token, _ = recruiter_account(
        client, f"ml-mrec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    cand_token, cand_user = prepared_candidate(
        client, db_session, f"ml-cand-{uuid.uuid4().hex[:8]}@example.com", ["ML", "Python", "Kubernetes"]
    )
    match = client.get(
        f"/api/v1/candidates/{cand_user['candidate_id']}/jobs/{job_id}/match",
        headers=bearer(cand_token),
    )
    assert match.status_code == 200, match.text
    body = match.json()
    assert body["current_match"] is not None
    if body["scoring_mode"] == "trained":
        assert body["model_version"] == model.version
        assert body["model_relevance_score"] is not None
        assert body["ml_explanations"]
    else:
        assert body["model_version"] is None
        assert body["fallback_reason"]
    from app.models import MatchRun

    run = db_session.query(MatchRun).order_by(MatchRun.created_at.desc()).first()
    assert run is not None
    assert run.scoring_mode == body["scoring_mode"]
    assert run.model_version == body["model_version"]
    assert run.current_match is not None


def test_current_real_dataset_skips_training(
    client: TestClient, db_session: Session, seeded_ontology, tmp_path: Path
) -> None:
    from app.modules.ml.service import DatasetService
    from tests.test_datasets import _scenario

    _scenario(client, db_session)
    built = DatasetService(db_session).build_rows()
    assert len(built["rows"]) == 3
    assert built["positive_count"] == 2
    assert built["negative_count"] == 1
    from ml.pipeline import SKIPPED, train

    result = train(built["rows"], dataset_id="real-phase9", artifact_root=tmp_path, **TRAIN_KW)
    assert result["status"] == SKIPPED
    assert result["artifact_dir"] is None
    assert not list(tmp_path.rglob("model.json"))
    assert not list(tmp_path.rglob("metadata.json"))
