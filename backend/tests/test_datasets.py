"""Phase 9 dataset snapshots. No training, no fake labels, no accuracy."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import FeatureSnapshot, MatchRun, MlModel, MlTrainingRun, RecruiterDecision
from tests.phase9_helpers import (
    admin_token,
    bearer,
    job_with_scenario_skills,
    prepared_candidate,
    recruiter_account,
    set_skills,
)

LEAKAGE = {"label", "shortlist", "reject", "note", "reason", "resume_text"}
PROTECTED = {
    "gender",
    "religion",
    "caste",
    "race",
    "ethnicity",
    "disability",
    "age",
    "name",
    "address",
}


def _scenario(client: TestClient, db_session: Session):
    rec_token, _ = recruiter_account(
        client, f"ds-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    a_token, a_user = prepared_candidate(
        client, db_session, f"ds-a-{uuid.uuid4().hex[:8]}@example.com", ["ML", "Python", "Docker"]
    )
    _, b_user = prepared_candidate(
        client, db_session, f"ds-b-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, c_user = prepared_candidate(
        client,
        db_session,
        f"ds-c-{uuid.uuid4().hex[:8]}@example.com",
        ["Machine Learning", "Python", "Kubernetes"],
    )
    listed = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    assert listed.status_code == 200, listed.text
    for cid, action in (
        (a_user["candidate_id"], "shortlist"),
        (b_user["candidate_id"], "reject"),
        (c_user["candidate_id"], "shortlist"),
    ):
        response = client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
            headers=bearer(rec_token),
            json={"action": action},
        )
        assert response.status_code == 201, response.text
    return rec_token, job_id, a_token, a_user, b_user, c_user


def test_scenario_training_labels_and_metadata(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, job_id, _, a_user, b_user, c_user = _scenario(client, db_session)
    admin = admin_token(client, db_session, f"ds-admin-{uuid.uuid4().hex[:8]}@example.com")
    created = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["trained"] is False
    assert body["note"].startswith("No trained model")
    assert body["positive_count"] == 2
    assert body["negative_count"] == 1
    assert body["row_count"] == 3
    assert body["sufficient_for_training_experiment"] is False
    labels = {row["candidate_id"]: row["label"] for row in body["rows"]}
    assert labels[a_user["candidate_id"]] == 1
    assert labels[b_user["candidate_id"]] == 0
    assert labels[c_user["candidate_id"]] == 1
    assert set(labels) == {a_user["candidate_id"], b_user["candidate_id"], c_user["candidate_id"]}
    dumped = json.dumps(body["rows"])
    assert "private recruiter note" not in dumped
    for row in body["rows"]:
        features = row["features"]
        assert "label" not in features
        assert "job_id" not in features
        assert "candidate_id" not in features
        assert row["grouping"]["job_id"] == job_id
        assert row["feature_schema_version"] in {"feature-schema-v1", "feature-schema-v2"}
        assert row["ontology_version"] == "seed-0.1"
        assert row["embedding_model_name"]
        assert row["feature_snapshot_id"]
        assert "current_match" in features
        assert LEAKAGE.isdisjoint(features)
        assert PROTECTED.isdisjoint({key.lower() for key in features})
        assert "resume_text" not in dumped.lower()
    assert db_session.query(MlTrainingRun).count() == 0
    assert db_session.query(MlModel).count() == 0
    rec_denied = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(rec_token))
    assert rec_denied.status_code == 403


def test_point_in_time_selects_t1_not_t3(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"pit-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    _, cand_user = prepared_candidate(
        client, db_session, f"pit-{uuid.uuid4().hex[:8]}@example.com", ["ML", "Python", "Docker"]
    )
    cid = cand_user["candidate_id"]
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    t1 = (
        db_session.query(FeatureSnapshot)
        .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
        .filter(MatchRun.candidate_id == uuid.UUID(cid), MatchRun.job_id == uuid.UUID(job_id))
        .order_by(FeatureSnapshot.created_at.asc())
        .first()
    )
    assert t1 is not None
    decided = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    assert decided.status_code == 201, decided.text
    t1_id = decided.json()["feature_snapshot_id"]
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    snaps = (
        db_session.query(FeatureSnapshot)
        .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
        .filter(MatchRun.candidate_id == uuid.UUID(cid), MatchRun.job_id == uuid.UUID(job_id))
        .all()
    )
    assert len(snaps) >= 2
    t3 = max(snaps, key=lambda row: (row.created_at, row.id))
    decision = db_session.get(RecruiterDecision, uuid.UUID(decided.json()["id"]))
    t1_row = db_session.get(FeatureSnapshot, uuid.UUID(t1_id))
    assert decision is not None and t1_row is not None
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1_row.created_at = base
    decision.created_at = base + timedelta(hours=1)
    t3.created_at = base + timedelta(hours=2)
    db_session.flush()
    db_session.expire_all()
    admin = admin_token(client, db_session, f"pit-admin-{uuid.uuid4().hex[:8]}@example.com")
    body = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    row = next(item for item in body["rows"] if item["candidate_id"] == cid)
    assert row["feature_snapshot_id"] == t1_id
    assert row["feature_snapshot_id"] != str(t3.id)


def test_future_profile_change_does_not_replace_snapshot(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, job_id, a_token, a_user, _, _ = _scenario(client, db_session)
    cid = a_user["candidate_id"]
    original = (
        db_session.query(RecruiterDecision)
        .filter(RecruiterDecision.candidate_id == uuid.UUID(cid))
        .one()
    )
    original_snap = original.feature_snapshot_id
    set_skills(client, a_token, cid, ["ML", "Python", "Docker", "Kubernetes"])
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    db_session.expire_all()
    stored = (
        db_session.query(RecruiterDecision)
        .filter(RecruiterDecision.candidate_id == uuid.UUID(cid))
        .one()
    )
    assert stored.feature_snapshot_id == original_snap
    admin = admin_token(client, db_session, f"leak-admin-{uuid.uuid4().hex[:8]}@example.com")
    body = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    row = next(item for item in body["rows"] if item["candidate_id"] == cid)
    assert row["feature_snapshot_id"] == str(original_snap)


def test_dataset_exclusions_and_version_immutability(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"ex-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    _, undecided = prepared_candidate(
        client, db_session, f"ex-none-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, reviewed = prepared_candidate(
        client, db_session, f"ex-rev-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, late = prepared_candidate(
        client, db_session, f"ex-late-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, good = prepared_candidate(
        client, db_session, f"ex-good-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, invalid = prepared_candidate(
        client, db_session, f"ex-bad-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    client.post(
        f"/api/v1/jobs/{job_id}/candidates/{reviewed['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "review"},
    )
    late_decision = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{late['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    assert late_decision.status_code == 201
    late_row = db_session.get(RecruiterDecision, uuid.UUID(late_decision.json()["id"]))
    late_row.feature_snapshot_id = None
    late_row.match_run_id = None
    late_row.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db_session.flush()
    good_resp = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{good['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "reject"},
    )
    assert good_resp.status_code == 201
    invalid_resp = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{invalid['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    snap = db_session.get(FeatureSnapshot, uuid.UUID(invalid_resp.json()["feature_snapshot_id"]))
    snap.feature_schema_version = "feature-schema-v99"
    snap.features = {**snap.features, "feature_schema_version": "feature-schema-v99"}
    flag_modified(snap, "features")
    db_session.flush()

    admin = admin_token(client, db_session, f"ex-admin-{uuid.uuid4().hex[:8]}@example.com")
    v1 = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    reasons = v1["exclusion_reasons"]
    assert reasons.get("no_decision", 0) >= 1
    assert reasons.get("review_unlabeled", 0) >= 1
    assert reasons.get("missing_feature_snapshot", 0) >= 1 or reasons.get(
        "feature_snapshot_after_decision", 0
    ) >= 1
    assert reasons.get("invalid_schema", 0) >= 1
    included = {row["candidate_id"] for row in v1["rows"]}
    assert good["candidate_id"] in included
    assert undecided["candidate_id"] not in included
    assert reviewed["candidate_id"] not in included
    assert invalid["candidate_id"] not in included
    assert v1["negative_count"] >= 1

    extra_token, extra_user = prepared_candidate(
        client, db_session, f"ex-v2-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    assert extra_token
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    client.post(
        f"/api/v1/jobs/{job_id}/candidates/{extra_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    v2 = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    listed = client.get("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    assert {item["id"] for item in listed} >= {v1["id"], v2["id"]}
    fetched = client.get(f"/api/v1/admin/datasets/snapshots/{v1['id']}", headers=bearer(admin)).json()
    assert fetched["row_count"] == v1["row_count"]
    assert fetched["checksum"] == v1["checksum"]
    assert extra_user["candidate_id"] not in {row["candidate_id"] for row in fetched["rows"]}
    assert extra_user["candidate_id"] in {row["candidate_id"] for row in v2["rows"]}
    assert v2["id"] != v1["id"]


def test_invalid_ontology_and_feature_values_excluded(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"val-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    _, onto_user = prepared_candidate(
        client, db_session, f"val-onto-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, bad_user = prepared_candidate(
        client, db_session, f"val-bad-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, ok_user = prepared_candidate(
        client, db_session, f"val-ok-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    for cid, action in (
        (onto_user["candidate_id"], "shortlist"),
        (bad_user["candidate_id"], "reject"),
        (ok_user["candidate_id"], "shortlist"),
    ):
        response = client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
            headers=bearer(rec_token),
            json={"action": action},
        )
        assert response.status_code == 201, response.text
    onto_decision = (
        db_session.query(RecruiterDecision)
        .filter(RecruiterDecision.candidate_id == uuid.UUID(onto_user["candidate_id"]))
        .one()
    )
    onto_snap = db_session.get(FeatureSnapshot, onto_decision.feature_snapshot_id)
    features = dict(onto_snap.features)
    features.pop("ontology_version", None)
    onto_snap.features = features
    flag_modified(onto_snap, "features")
    onto_snap.match_run.ontology_version_id = None
    bad_decision = (
        db_session.query(RecruiterDecision)
        .filter(RecruiterDecision.candidate_id == uuid.UUID(bad_user["candidate_id"]))
        .one()
    )
    bad_snap = db_session.get(FeatureSnapshot, bad_decision.feature_snapshot_id)
    bad_snap.features = {**bad_snap.features, "current_match": 9.0}
    flag_modified(bad_snap, "features")
    db_session.flush()
    admin = admin_token(client, db_session, f"val-admin-{uuid.uuid4().hex[:8]}@example.com")
    body = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    included = {row["candidate_id"] for row in body["rows"]}
    assert ok_user["candidate_id"] in included
    assert onto_user["candidate_id"] not in included
    assert bad_user["candidate_id"] not in included
    assert body["exclusion_reasons"].get("unknown_ontology_version", 0) >= 1
    assert body["exclusion_reasons"].get("invalid_feature_values", 0) >= 1
    assert db_session.query(MlTrainingRun).count() == 0
    assert db_session.query(MlModel).count() == 0


def test_phase9_does_not_import_xgboost() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for path in [
        root / "app" / "modules" / "ml" / "service.py",
        root / "app" / "modules" / "analytics" / "service.py",
        root.parent / "ml" / "train.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "import xgboost" not in text
        assert "from xgboost" not in text
