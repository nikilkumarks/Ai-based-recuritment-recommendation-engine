from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditLog, Candidate, CandidateProfile, ExtractionRevision, Resume
from app.models.enums import ConfirmationStatus
from app.modules.documents.storage import resume_storage_key
from tests.auth_helpers import login_user, register_user
from tests.fixtures.resume_docs import (
    blank_pdf,
    malformed_docx,
    malformed_pdf,
    normal_docx,
    normal_pdf,
    pdf_containing,
)


def _auth(
    client: TestClient, email: str, *, role: str = "candidate", org: str | None = None
) -> tuple[str, str]:
    register_user(
        client,
        email=email,
        role=role,
        organization_name=org,
    )
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"].get("candidate_id")


def _upload(client: TestClient, token: str, candidate_id: str, filename: str, data: bytes, mime: str):
    return client.post(
        f"/api/v1/candidates/{candidate_id}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, data, mime)},
    )


def test_candidate_uploads_own_resume(client: TestClient, db_session: Session) -> None:
    token, cid = _auth(client, "up@example.com")
    response = _upload(client, token, cid, "cv.pdf", normal_pdf(), "application/pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parse_status"] == "ready"
    assert body["filename"] == "cv.pdf"
    assert "storage_key" not in body
    resume = db_session.query(Resume).one()
    revision = db_session.query(ExtractionRevision).one()
    assert "Ada Lovelace" in revision.extraction_payload["normalized_text"]
    assert resume.sha256


def test_candidate_cannot_upload_to_another_candidate(client: TestClient) -> None:
    token_a, _cid_a = _auth(client, "a@example.com")
    _token_b, cid_b = _auth(client, "b@example.com")
    response = _upload(client, token_a, cid_b, "cv.pdf", normal_pdf(), "application/pdf")
    assert response.status_code == 403


def test_unauthenticated_upload_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "u@example.com")
    response = client.post(
        f"/api/v1/candidates/{cid}/resumes",
        files={"file": ("cv.pdf", normal_pdf(), "application/pdf")},
    )
    assert response.status_code == 401
    assert token


def test_unsupported_mime_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "mime@example.com")
    response = _upload(client, token, cid, "note.txt", b"hello world this is text", "text/plain")
    assert response.status_code == 415


def test_incorrect_magic_bytes_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "magic@example.com")
    response = _upload(client, token, cid, "cv.pdf", b"\x89PNG\r\n\x1a\n" + b"x" * 40, "application/pdf")
    assert response.status_code == 400


def test_oversized_file_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "big@example.com")
    settings = get_settings()
    previous = settings.max_resume_bytes
    settings.max_resume_bytes = 64
    try:
        response = _upload(client, token, cid, "cv.pdf", b"%PDF-1.4\n" + b"x" * 200, "application/pdf")
        assert response.status_code == 413
    finally:
        settings.max_resume_bytes = previous


def test_empty_file_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "empty@example.com")
    response = _upload(client, token, cid, "cv.pdf", b"", "application/pdf")
    assert response.status_code == 400


def test_path_traversal_filename_rejected(client: TestClient) -> None:
    token, cid = _auth(client, "path@example.com")
    response = _upload(client, token, cid, "..\\..\\etc\\passwd.pdf", normal_pdf(), "application/pdf")
    assert response.status_code == 400


def test_resume_metadata_isolated_between_candidates(client: TestClient) -> None:
    token_a, cid_a = _auth(client, "iso-a@example.com")
    token_b, cid_b = _auth(client, "iso-b@example.com")
    uploaded = _upload(client, token_a, cid_a, "cv.pdf", normal_pdf(), "application/pdf")
    resume_id = uploaded.json()["id"]
    other = client.get(
        f"/api/v1/candidates/{cid_a}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert other.status_code == 403
    listed = client.get(
        f"/api/v1/candidates/{cid_a}/resumes",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert listed.status_code == 403
    assert cid_b


def test_delete_requires_ownership(client: TestClient) -> None:
    token_a, cid_a = _auth(client, "del-a@example.com")
    token_b, _cid_b = _auth(client, "del-b@example.com")
    uploaded = _upload(client, token_a, cid_a, "cv.pdf", normal_pdf(), "application/pdf")
    resume_id = uploaded.json()["id"]
    denied = client.delete(
        f"/api/v1/candidates/{cid_a}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert denied.status_code == 403
    ok = client.delete(
        f"/api/v1/candidates/{cid_a}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert ok.status_code == 200


def test_recruiter_cannot_access_resume_outside_scope(client: TestClient) -> None:
    _token_c, cid = _auth(client, "pool-c@example.com")
    token_r, _ = _auth(client, "pool-r@example.com", role="recruiter", org="Pool Corp")
    listed = client.get(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token_r}"},
    )
    assert listed.status_code == 403


def test_recruiter_can_view_metadata_when_in_scope(client: TestClient, db_session: Session) -> None:
    token_c, cid = _auth(client, "vis-c@example.com")
    token_r, _ = _auth(client, "vis-r@example.com", role="recruiter", org="Visible Corp")
    candidate = db_session.query(Candidate).filter(Candidate.id == cid).one()
    candidate.preferences = {"discoverable": True}
    db_session.flush()
    uploaded = _upload(client, token_c, cid, "cv.pdf", normal_pdf(), "application/pdf")
    resume_id = uploaded.json()["id"]
    listed = client.get(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token_r}"},
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == resume_id
    assert "storage_key" not in listed.json()["items"][0]
    upload_denied = _upload(client, token_r, cid, "cv.pdf", normal_pdf(), "application/pdf")
    assert upload_denied.status_code == 403


def test_delete_removes_revisions_keeps_confirmed_profile(
    client: TestClient, db_session: Session, blob_store
) -> None:
    token, cid = _auth(client, "keep@example.com")
    uploaded = _upload(client, token, cid, "cv.pdf", normal_pdf(), "application/pdf")
    resume_id = uploaded.json()["id"]
    resume = db_session.query(Resume).one()
    key = resume.storage_key
    confirmed = client.post(
        f"/api/v1/candidates/{cid}/profile/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirmed.status_code == 200, confirmed.text
    profile_id = confirmed.json()["id"]
    assert blob_store.exists(key)
    deleted = client.delete(
        f"/api/v1/candidates/{cid}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 200
    db_session.expire_all()
    assert db_session.get(Resume, resume_id) is None
    assert db_session.query(ExtractionRevision).count() == 0
    kept = db_session.get(CandidateProfile, profile_id)
    assert kept is not None
    assert kept.confirmation_status == ConfirmationStatus.CONFIRMED.value
    assert kept.source_revision_id is None
    assert blob_store.exists(key) is False


def test_audit_omits_file_contents(client: TestClient, db_session: Session) -> None:
    token, cid = _auth(client, "aud@example.com")
    _upload(client, token, cid, "cv.pdf", pdf_containing("SECRETTEXTXYZ"), "application/pdf")
    logs = db_session.query(AuditLog).filter(AuditLog.action.like("resume_%")).all()
    assert logs
    dumped = str([row.audit_metadata for row in logs]).lower()
    assert "secrettextxyz" not in dumped
    assert "normalized_text" not in dumped


def test_same_candidate_duplicate_checksum(client: TestClient, db_session: Session) -> None:
    token, cid = _auth(client, "dup@example.com")
    data = normal_pdf()
    first = _upload(client, token, cid, "cv.pdf", data, "application/pdf")
    second = _upload(client, token, cid, "cv-copy.pdf", data, "application/pdf")
    assert first.status_code == 201
    assert second.json()["duplicate"] is True
    assert second.json()["id"] == first.json()["id"]
    assert db_session.query(Resume).count() == 1


def test_different_candidates_share_blob_not_authorization(
    client: TestClient, db_session: Session, blob_store
) -> None:
    token_a, cid_a = _auth(client, "share-a@example.com")
    token_b, cid_b = _auth(client, "share-b@example.com")
    data = normal_pdf()
    a = _upload(client, token_a, cid_a, "a.pdf", data, "application/pdf")
    b = _upload(client, token_b, cid_b, "b.pdf", data, "application/pdf")
    assert a.json()["id"] != b.json()["id"]
    rows = db_session.query(Resume).all()
    assert len(rows) == 2
    assert rows[0].sha256 == rows[1].sha256
    assert rows[0].storage_key == resume_storage_key(rows[0].sha256)
    assert blob_store.exists(rows[0].storage_key)
    denied = client.get(
        f"/api/v1/candidates/{cid_a}/resumes/{a.json()['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert denied.status_code == 403


def test_malformed_pdf_upload_fails_safely(client: TestClient) -> None:
    token, cid = _auth(client, "badpdf@example.com")
    response = _upload(client, token, cid, "cv.pdf", malformed_pdf(), "application/pdf")
    assert response.status_code == 201
    assert response.json()["parse_status"] == "failed"


def test_textless_pdf_needs_ocr(client: TestClient) -> None:
    token, cid = _auth(client, "ocr@example.com")
    response = _upload(client, token, cid, "scan.pdf", blank_pdf(), "application/pdf")
    assert response.status_code == 201
    assert response.json()["parse_status"] == "needs_ocr"


def test_malformed_docx_upload_fails_safely(client: TestClient) -> None:
    token, cid = _auth(client, "baddocx@example.com")
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response = _upload(client, token, cid, "cv.docx", malformed_docx(), mime)
    assert response.status_code == 400


def test_valid_docx_produces_revision(client: TestClient, db_session: Session) -> None:
    token, cid = _auth(client, "docx@example.com")
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response = _upload(client, token, cid, "cv.docx", normal_docx(), mime)
    assert response.status_code == 201, response.text
    assert response.json()["parse_status"] == "ready"
    revision = db_session.query(ExtractionRevision).one()
    assert "Ada Lovelace" in revision.extraction_payload["normalized_text"]
