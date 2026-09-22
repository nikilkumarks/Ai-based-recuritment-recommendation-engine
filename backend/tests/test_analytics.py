"""Phase 9 descriptive analytics. Not hiring success and not model accuracy."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Application
from app.models.enums import ApplicationStatus
from tests.phase9_helpers import (
    admin_token,
    bearer,
    job_with_scenario_skills,
    prepared_candidate,
    recruiter_account,
)


def test_recruiter_analytics_org_isolation_and_counts(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_token, _ = recruiter_account(
        client, f"an-rec-{uuid.uuid4().hex[:8]}@example.com", f"Org {uuid.uuid4().hex[:6]}"
    )
    other_token, _ = recruiter_account(
        client, f"an-other-{uuid.uuid4().hex[:8]}@example.com", f"Other {uuid.uuid4().hex[:6]}"
    )
    job_id = job_with_scenario_skills(client, rec_token)
    a_token, a_user = prepared_candidate(
        client, db_session, f"an-a-{uuid.uuid4().hex[:8]}@example.com", ["ML", "Python", "Docker"]
    )
    _, b_user = prepared_candidate(
        client, db_session, f"an-b-{uuid.uuid4().hex[:8]}@example.com", ["Python"]
    )
    listed = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=bearer(rec_token))
    assert listed.status_code == 200, listed.text
    client.post(
        f"/api/v1/jobs/{job_id}/candidates/{a_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "shortlist"},
    )
    client.post(
        f"/api/v1/jobs/{job_id}/candidates/{b_user['candidate_id']}/decisions",
        headers=bearer(rec_token),
        json={"action": "reject"},
    )
    db_session.add(
        Application(
            candidate_id=uuid.UUID(a_user["candidate_id"]),
            job_id=uuid.UUID(job_id),
            status=ApplicationStatus.APPLIED.value,
        )
    )
    db_session.flush()

    overview = client.get("/api/v1/analytics/recruiter/overview", headers=bearer(rec_token))
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["jobs"] == 1
    assert body["candidates"] == 2
    assert body["applications"] == 1
    assert body["shortlist_count"] == 1
    assert body["reject_count"] == 1
    assert "hire" not in body
    assert "hiring" not in body["disclaimer"].lower() or "not" in body["disclaimer"].lower()
    assert body["shortlist_rate"] == 0.5

    isolated = client.get("/api/v1/analytics/recruiter/overview", headers=bearer(other_token))
    assert isolated.status_code == 200
    other = isolated.json()
    assert other["jobs"] == 0
    assert other["shortlist_count"] == 0
    assert other["reject_count"] == 0

    skills = client.get("/api/v1/analytics/recruiter/skills", headers=bearer(rec_token)).json()
    demand = {item["name"]: item["count"] for item in skills["required_demand"]}
    assert demand["Machine Learning"] == 1
    assert demand["Python"] == 1
    assert demand["Kubernetes"] == 1
    preferred = {item["name"]: item["count"] for item in skills["preferred_demand"]}
    assert preferred["Docker"] == 1
    supply = {item["name"]: item["count"] for item in skills["candidate_supply"]}
    assert supply["Python"] == 2
    other_skills = client.get("/api/v1/analytics/recruiter/skills", headers=bearer(other_token)).json()
    assert other_skills["required_demand"] == []

    matching = client.get("/api/v1/analytics/recruiter/matching", headers=bearer(rec_token)).json()
    assert sum(item["count"] for item in matching["current_match"]) >= 1
    funnel = client.get("/api/v1/analytics/recruiter/funnel", headers=bearer(rec_token)).json()
    assert funnel["shortlisted"] == 1
    assert funnel["rejected"] == 1
    assert "hire_rate" not in funnel

    candidate_denied = client.get("/api/v1/analytics/recruiter/overview", headers=bearer(a_token))
    assert candidate_denied.status_code == 403
    own = client.get(
        f"/api/v1/analytics/candidates/{a_user['candidate_id']}/overview",
        headers=bearer(a_token),
    )
    assert own.status_code == 200
    other_cand = client.get(
        f"/api/v1/analytics/candidates/{b_user['candidate_id']}/overview",
        headers=bearer(a_token),
    )
    assert other_cand.status_code == 403

    admin = admin_token(client, db_session, f"an-admin-{uuid.uuid4().hex[:8]}@example.com")
    admin_overview = client.get("/api/v1/analytics/admin/overview", headers=bearer(admin))
    assert admin_overview.status_code == 200
    assert admin_overview.json()["shortlist_count"] >= 1
    rec_admin = client.get("/api/v1/analytics/admin/overview", headers=bearer(rec_token))
    assert rec_admin.status_code == 403
