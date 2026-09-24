"""Phase 9 recruiter decisions. Behavioral labels, not hiring outcomes."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog, FeatureSnapshot, MatchRun, RecruiterDecision
from tests.phase9_helpers import (
    add_org_recruiter,
    admin_token,
    bearer,
    job_with_scenario_skills,
    prepared_candidate,
    recruiter_account,
)


def test_shortlist_and_reject_link_pre_decision_snapshots(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, rec_user = recruiter_account(
        client, f"dec-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    a_token, a_user = prepared_candidate(
        client, db_session, f"a-{uuid.uuid4().hex[:8]}@example.com", ["ML", "Python", "Docker"]
    )
    _, b_user = prepared_candidate(
        client, db_session, f"b-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    _, c_user = prepared_candidate(
        client,
        db_session,
        f"c-{uuid.uuid4().hex[:8]}@example.com",
        ["Machine Learning", "Python", "Kubernetes"],
    )
    listed = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    assert listed.status_code == 200, listed.text
    by_id = {item["candidate_id"]: item for item in listed.json()["items"]}
    assert set(by_id) == {a_user["candidate_id"], b_user["candidate_id"], c_user["candidate_id"]}

    snapshots_before = {
        str(run.candidate_id): snap
        for snap, run in db_session.query(FeatureSnapshot, MatchRun)
        .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
        .filter(MatchRun.job_id == uuid.UUID(job_id))
        .all()
    }

    short_a = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{a_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist", "reason": "strong_skill_match", "note": "private recruiter note"},
    )
    assert short_a.status_code == 201, short_a.text
    reject_b = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{b_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "reject", "reason": "skill_gap"},
    )
    assert reject_b.status_code == 201, reject_b.text
    short_c = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{c_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    assert short_c.status_code == 201, short_c.text

    for body, cid in (
        (short_a.json(), a_user["candidate_id"]),
        (reject_b.json(), b_user["candidate_id"]),
        (short_c.json(), c_user["candidate_id"]),
    ):
        assert body["feature_snapshot_id"] is not None
        assert body["match_run_id"] is not None
        assert body["feature_snapshot_id"] == str(snapshots_before[cid].id)
        snap = db_session.get(FeatureSnapshot, uuid.UUID(body["feature_snapshot_id"]))
        decision = db_session.get(RecruiterDecision, uuid.UUID(body["id"]))
        assert snap is not None and decision is not None
        assert snap.created_at <= decision.created_at

    history = client.get(
        f"/api/v1/jobs/{job_id}/candidates/{a_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
    )
    assert history.status_code == 200
    payload = history.json()
    assert payload["current_action"] == "shortlist"
    assert payload["append_only"] is True
    assert payload["items"][0]["note"] == "private recruiter note"
    hidden = client.get(
        f"/api/v1/jobs/{job_id}/candidates/{a_user['candidate_id']}/decisions",
        headers=bearer(a_token),
    )
    assert hidden.status_code == 403
    relisted = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    current = {item["candidate_id"]: item["current_decision"] for item in relisted.json()["items"]}
    assert current[a_user["candidate_id"]] == "shortlist"
    assert current[b_user["candidate_id"]] == "reject"
    assert current[c_user["candidate_id"]] == "shortlist"
    audits = {row.action for row in db_session.query(AuditLog).all()}
    assert "recruiter_shortlisted" in audits
    assert "recruiter_rejected" in audits
    for row in db_session.query(AuditLog).all():
        assert "private recruiter note" not in str(row.audit_metadata)


def test_append_only_history_and_candidate_cannot_create(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"dec-hist-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    cand_token, cand_user = prepared_candidate(
        client, db_session, f"hist-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    cid = cand_user["candidate_id"]
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    first = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    second = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_token),
        json={"action": "reject"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    listed = client.get(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_token),
    ).json()
    assert [item["action"] for item in listed["items"]] == ["shortlist", "reject"]
    assert listed["current_action"] == "reject"
    denied = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(cand_token),
        json={"action": "shortlist"},
    )
    assert denied.status_code == 403


def test_recruiter_cannot_decide_on_foreign_org_job(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_a, _ = recruiter_account(
        client, f"dec-a-{uuid.uuid4().hex[:8]}@example.com", f"OrgA {uuid.uuid4().hex[:6]}"
    )
    rec_b, _ = recruiter_account(
        client, f"dec-b-{uuid.uuid4().hex[:8]}@example.com", f"OrgB {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_a)
    _, cand_user = prepared_candidate(
        client, db_session, f"foreign-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    blocked = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cand_user['candidate_id']}/decisions",
        headers=bearer(rec_b),
        json={"action": "shortlist"},
    )
    assert blocked.status_code == 403
    listed = client.get(
        f"/api/v1/jobs/{job_id}/candidates/{cand_user['candidate_id']}/decisions",
        headers=bearer(rec_b),
    )
    assert listed.status_code == 403


def test_conflicting_recruiters_keep_both_events(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_a, rec_user = recruiter_account(
        client, f"conf-a-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    rec_b = add_org_recruiter(
        client,
        db_session,
        email=f"conf-b-{uuid.uuid4().hex[:8]}@example.com",
        organization_id=uuid.UUID(rec_user["organization_id"]),
    )
    job_id = job_with_scenario_skills(client, rec_a)
    _, cand_user = prepared_candidate(
        client, db_session, f"conf-c-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    cid = cand_user["candidate_id"]
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_a))
    first = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_a),
        json={"action": "shortlist"},
    )
    second = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_b),
        json={"action": "reject"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    history = client.get(
        f"/api/v1/jobs/{job_id}/candidates/{cid}/decisions",
        headers=bearer(rec_a),
    ).json()
    assert [item["action"] for item in history["items"]] == ["shortlist", "reject"]
    assert history["current_action"] == "reject"
    admin = admin_token(client, db_session, f"conf-admin-{uuid.uuid4().hex[:8]}@example.com")
    snapshot = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin))
    assert snapshot.status_code == 201, snapshot.text
    rows = snapshot.json()["rows"]
    match = next(item for item in rows if item["candidate_id"] == cid)
    assert match["label"] == 0
    assert match["decision_conflict"] is True


def test_review_is_not_a_binary_label(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"rev-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    _, cand_user = prepared_candidate(
        client, db_session, f"rev-c-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    reviewed = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cand_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "review"},
    )
    assert reviewed.status_code == 201
    admin = admin_token(client, db_session, f"rev-admin-{uuid.uuid4().hex[:8]}@example.com")
    snapshot = client.post("/api/v1/admin/datasets/snapshots", headers=bearer(admin)).json()
    assert all(row["candidate_id"] != cand_user["candidate_id"] for row in snapshot["rows"])
    assert snapshot["exclusion_reasons"].get("review_unlabeled", 0) >= 1
    hire = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{cand_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "hire"},
    )
    assert hire.status_code == 201
    assert db_session.query(MatchRun).count() >= 1
