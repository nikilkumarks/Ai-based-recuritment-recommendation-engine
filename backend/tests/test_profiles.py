from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog, Candidate, CandidateProfile, CandidateSkill, ExtractionRevision
from app.models.enums import ConfirmationStatus
from tests.auth_helpers import login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines, sectioned_pdf


def _auth(client: TestClient, email: str, *, role: str = "candidate", org: str | None = None):
    register_user(client, email=email, role=role, organization_name=org)
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def test_upload_runs_nlp_and_creates_draft(client: TestClient, db_session: Session) -> None:
    token, user = _auth(client, "nlp-up@example.com")
    cid = user["candidate_id"]
    lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
    response = client.post(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    revision = db_session.query(ExtractionRevision).one()
    nlp = revision.extraction_payload.get("nlp") or {}
    assert nlp.get("status") == "ready"
    assert nlp.get("pipeline_version") == "nlp-v1"
    assert "profile_draft" in nlp
    profile = client.get(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["draft"]["confirmation_status"] == "draft"
    skills = [item["raw_text"] for item in profile.json()["draft"]["draft"]["skills"]]
    assert any(value.upper() == "ML" for value in skills)
    assert any(value.casefold() == "machine learning" for value in skills)


def test_candidate_edit_and_confirm_persists(client: TestClient, db_session: Session) -> None:
    token, user = _auth(client, "nlp-confirm@example.com")
    cid = user["candidate_id"]
    client.post(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", sectioned_pdf(), "application/pdf")},
    )
    edited = client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary": "Edited summary that the candidate wrote."},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["summary"] == "Edited summary that the candidate wrote."
    confirmed = client.post(
        f"/api/v1/candidates/{cid}/profile/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmation_status"] == "confirmed"
    row = db_session.query(CandidateProfile).filter(
        CandidateProfile.confirmation_status == ConfirmationStatus.CONFIRMED.value
    ).one()
    assert row.summary == "Edited summary that the candidate wrote."


def test_reparse_does_not_overwrite_confirmed(client: TestClient, db_session: Session) -> None:
    token, user = _auth(client, "nlp-lock@example.com")
    cid = user["candidate_id"]
    first = client.post(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", sectioned_pdf(), "application/pdf")},
    )
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary": "Confirmed by candidate."},
    )
    client.post(
        f"/api/v1/candidates/{cid}/profile/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = first.json()["id"]
    client.post(
        f"/api/v1/candidates/{cid}/resumes/{resume_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert body["confirmed"]["summary"] == "Confirmed by candidate."
    assert body["draft"] is not None
    assert body["draft"]["confirmation_status"] == "draft"
    confirmed_rows = (
        db_session.query(CandidateProfile)
        .filter(CandidateProfile.confirmation_status == ConfirmationStatus.CONFIRMED.value)
        .all()
    )
    assert all(row.summary == "Confirmed by candidate." for row in confirmed_rows)


def test_profile_isolation_and_audit_without_pii(client: TestClient, db_session: Session) -> None:
    token_a, user_a = _auth(client, "nlp-a@example.com")
    token_b, _user_b = _auth(client, "nlp-b@example.com")
    cid_a = user_a["candidate_id"]
    client.post(
        f"/api/v1/candidates/{cid_a}/resumes",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("cv.pdf", sectioned_pdf(), "application/pdf")},
    )
    denied = client.get(
        f"/api/v1/candidates/{cid_a}/profile",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert denied.status_code == 403
    logs = db_session.query(AuditLog).filter(AuditLog.action.like("nlp_%")).all()
    dumped = str([row.audit_metadata for row in logs]).lower()
    assert "ada@example.com" not in dumped
    assert "98765" not in dumped


def test_confirmed_profile_survives_resume_delete(client: TestClient, db_session: Session) -> None:
    token, user = _auth(client, "nlp-keep@example.com")
    cid = user["candidate_id"]
    uploaded = client.post(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", sectioned_pdf(), "application/pdf")},
    )
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary": "Keep me."},
    )
    client.post(
        f"/api/v1/candidates/{cid}/profile/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    deleted = client.delete(
        f"/api/v1/candidates/{cid}/resumes/{uploaded.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 200
    db_session.expire_all()
    kept = (
        db_session.query(CandidateProfile)
        .filter(CandidateProfile.confirmation_status == ConfirmationStatus.CONFIRMED.value)
        .one()
    )
    assert kept.summary == "Keep me."
    assert db_session.query(Candidate).filter(Candidate.id == cid).one()
    assert db_session.query(CandidateSkill).count() == 0
