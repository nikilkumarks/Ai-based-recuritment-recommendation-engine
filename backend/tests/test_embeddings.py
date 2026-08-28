from __future__ import annotations

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Embedding, ProcessingJob, User
from app.models.enums import EmbeddingOwnerType, ProcessingJobStatus, UserRole, UserStatus
from app.modules.embeddings.compatibility import EncoderIdentity, classify_status
from app.modules.embeddings.encoder import HashingEncoder, get_encoder, reset_encoder, set_encoder
from app.modules.embeddings.hashing import content_hash
from app.modules.embeddings.service import EmbeddingService
from app.modules.embeddings.similarity import cosine_similarity, is_identical_cosine
from app.modules.identity.password import hash_password
from tests.auth_helpers import PASSWORD, login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_JD, ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines

MARKER = "UNIQUE_RESUME_TOKEN_XYZ_DO_NOT_LOG"


def test_encoder_cached() -> None:
    reset_encoder()
    first = get_encoder()
    second = get_encoder()
    assert first is second
    reset_encoder()


def test_hashing_encoder_dimension_and_stability() -> None:
    encoder = HashingEncoder(dimensions=8)
    assert encoder.dimensions == 8
    assert encoder.model_name == "hashing-encoder"
    left = encoder.encode("same text")
    right = encoder.encode("same text")
    assert len(left) == 8
    assert left == right
    assert cosine_similarity(left, left) == pytest.approx(1.0, abs=1e-6)
    changed = encoder.encode("different text")
    assert content_hash("hello") != content_hash("hello world")
    assert left != changed


def test_hashing_backend_does_not_claim_minilm() -> None:
    reset_encoder()
    encoder = get_encoder()
    assert isinstance(encoder, HashingEncoder)
    assert encoder.model_name == "hashing-encoder"
    assert encoder.model_version == "hashing-v1"
    assert encoder.dimensions == 8
    assert "minilm" not in encoder.model_name.lower()
    assert "sentence-transformers" not in encoder.model_name.lower()
    identity = encoder.identity("embedding-text-v1")
    assert identity.model_name == "hashing-encoder"
    reset_encoder()


def test_hashing_encoder_rejects_minilm_name() -> None:
    with pytest.raises(ValueError):
        HashingEncoder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def test_text_version_consistency(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.core.errors import UnprocessableError
    from app.modules.embeddings.constants import TEXT_VERSION_V1
    from app.modules.embeddings.text_builder import text_version

    get_settings.cache_clear()
    assert text_version() == TEXT_VERSION_V1
    monkeypatch.setenv("EMBEDDING_TEXT_VERSION", "embedding-text-v9")
    get_settings.cache_clear()
    with pytest.raises(UnprocessableError):
        text_version()
    monkeypatch.delenv("EMBEDDING_TEXT_VERSION", raising=False)
    get_settings.cache_clear()
    assert text_version() == TEXT_VERSION_V1


def test_cosine_identical_and_incompatible_dimension() -> None:
    from app.core.errors import IncompatibleEmbeddingError
    from app.modules.embeddings.similarity import require_dimension

    vector = [1.0, 0.0, 0.0]
    assert is_identical_cosine(cosine_similarity(vector, vector))
    with pytest.raises(IncompatibleEmbeddingError):
        cosine_similarity(vector, [1.0, 0.0])
    with pytest.raises(IncompatibleEmbeddingError):
        require_dimension([1.0, 0.0], 8)
    with pytest.raises(IncompatibleEmbeddingError):
        require_dimension([], 8)


def test_wrong_vector_dimension_is_rejected(db_session: Session) -> None:
    from app.core.errors import IncompatibleEmbeddingError

    class WrongDimEncoder:
        model_name = "hashing-encoder"
        model_version = "hashing-v1"
        dimensions = 8

        def encode(self, text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        def identity(self, text_version: str) -> EncoderIdentity:
            return EncoderIdentity(self.model_name, self.model_version, self.dimensions, text_version)

    service = EmbeddingService(db_session, encoder=WrongDimEncoder())
    with pytest.raises(IncompatibleEmbeddingError):
        service.encode_text("hello")
    with pytest.raises(IncompatibleEmbeddingError):
        service.similar_owners(query=[0.1, 0.2], owner_type=EmbeddingOwnerType.PROFILE.value)


def test_classify_missing_stale_incompatible() -> None:
    current = EncoderIdentity("hashing-encoder", "hashing-v1", 8, "embedding-text-v1")
    assert classify_status(row=None, current=current, content_hash="abc") == "missing"


def test_unauthenticated_candidate_embed_rejected(client: TestClient) -> None:
    denied = client.post("/api/v1/candidates/00000000-0000-0000-0000-000000000001/profile/embedding")
    assert denied.status_code == 401


def test_unconfirmed_profile_cannot_embed(client: TestClient) -> None:
    token, user = _candidate(client, "emb-draft@example.com")
    cid = user["candidate_id"]
    denied = client.post(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 409


def test_candidate_cannot_embed_another_candidate(client: TestClient, seeded_ontology) -> None:
    token_a, user_a = _candidate(client, "emb-a@example.com")
    token_b, user_b = _candidate(client, "emb-b@example.com")
    _upload_and_confirm(client, token_a, user_a["candidate_id"])
    denied = client.post(
        f"/api/v1/candidates/{user_a['candidate_id']}/profile/embedding",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert denied.status_code == 403


def test_profile_embed_reuses_and_hides_vectors(
    client: TestClient, db_session: Session, seeded_ontology, caplog
) -> None:
    caplog.set_level(logging.INFO)
    token, user = _candidate(client, "emb-ok@example.com")
    cid = user["candidate_id"]
    _upload_and_confirm(client, token, cid, extra_line=MARKER)
    first = client.post(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert "vector" not in body
    assert body["status"] == "current"
    assert body["dimensions"] == 8
    assert body["model_name"] == "hashing-encoder"
    assert "minilm" not in (body["model_name"] or "").lower()
    assert body["embedding_text_version"] == "embedding-text-v1"
    assert body["processing_job_id"]
    second = client.post(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.json()["reused"] is True
    assert second.json()["content_hash"] == body["content_hash"]
    rows = db_session.query(Embedding).filter(Embedding.owner_type == EmbeddingOwnerType.PROFILE.value).all()
    assert rows
    assert all(len(list(row.vector)) == 8 for row in rows)
    assert all(row.model_name == "hashing-encoder" for row in rows)
    assert all("minilm" not in row.model_name.lower() for row in rows)
    status = client.get(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.json()["status"] == "current"
    assert "vector" not in status.json()
    job = db_session.get(ProcessingJob, uuid.UUID(body["processing_job_id"]))
    assert job is not None
    assert job.status == ProcessingJobStatus.COMPLETED.value
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert MARKER not in joined
    assert ANNOTATED_RESUME.split("\n")[0] not in joined


def test_stale_after_source_change(client: TestClient, db_session: Session, seeded_ontology) -> None:
    token, user = _candidate(client, "emb-stale@example.com")
    cid = user["candidate_id"]
    _upload_and_confirm(client, token, cid)
    client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers={"Authorization": f"Bearer {token}"})
    row = db_session.query(Embedding).filter(Embedding.owner_type == EmbeddingOwnerType.PROFILE.value).one()
    row.content_hash = "0" * 64
    db_session.flush()
    status = client.get(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.json()["status"] == "stale"
    reembed = client.post(
        f"/api/v1/candidates/{cid}/profile/embedding?force=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reembed.json()["status"] == "current"
    assert reembed.json()["content_hash"] != "0" * 64
    assert reembed.json()["reused"] is False


def test_incompatible_model_and_text_version(db_session: Session) -> None:
    encoder = HashingEncoder(dimensions=8)
    row = Embedding(
        owner_type=EmbeddingOwnerType.PROFILE.value,
        owner_id=uuid.uuid4(),
        chunk_type="full",
        model_name="other-model",
        model_version="x",
        embedding_text_version="embedding-text-v1",
        dimensions=8,
        content_hash="a" * 64,
        vector=encoder.encode("hello"),
    )
    db_session.add(row)
    db_session.flush()
    current = encoder.identity("embedding-text-v1")
    assert classify_status(row=row, current=current, content_hash="a" * 64) == "incompatible"
    row.model_name = current.model_name
    row.model_version = current.model_version
    row.embedding_text_version = "embedding-text-v0"
    assert classify_status(row=row, current=current, content_hash="a" * 64) == "stale"
    row.embedding_text_version = current.embedding_text_version
    row.dimensions = 16
    assert classify_status(row=row, current=current, content_hash="a" * 64) == "incompatible"


def test_job_embed_auth_and_foreign_denied(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    rec_a, _ = _recruiter(client, "emb-rec-a@example.com", "Emb A")
    rec_b, _ = _recruiter(client, "emb-rec-b@example.com", "Emb B")
    created = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {rec_a}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    client.post(f"/api/v1/jobs/{job_id}/requirements/confirm", headers={"Authorization": f"Bearer {rec_a}"})
    embedded = client.post(f"/api/v1/jobs/{job_id}/embedding", headers={"Authorization": f"Bearer {rec_a}"})
    assert embedded.status_code == 200, embedded.text
    assert "vector" not in embedded.json()
    job_rows = db_session.query(Embedding).filter(Embedding.owner_type == EmbeddingOwnerType.JOB.value)
    assert job_rows.count() >= 1
    denied = client.post(f"/api/v1/jobs/{job_id}/embedding", headers={"Authorization": f"Bearer {rec_b}"})
    assert denied.status_code == 403


def test_unconfirmed_job_cannot_embed(client: TestClient) -> None:
    rec, _ = _recruiter(client, "emb-job-draft@example.com", "Emb Draft")
    created = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {rec}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    denied = client.post(f"/api/v1/jobs/{job_id}/embedding", headers={"Authorization": f"Bearer {rec}"})
    assert denied.status_code == 409


def test_admin_similarity_and_incompatible_compare(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    token, user = _candidate(client, "emb-sim@example.com")
    cid = user["candidate_id"]
    _upload_and_confirm(client, token, cid)
    client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers={"Authorization": f"Bearer {token}"})
    rec, _ = _recruiter(client, "emb-sim-rec@example.com", "Sim Org")
    job = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {rec}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    job_id = job.json()["id"]
    client.post(f"/api/v1/jobs/{job_id}/requirements/confirm", headers={"Authorization": f"Bearer {rec}"})
    client.post(f"/api/v1/jobs/{job_id}/embedding", headers={"Authorization": f"Bearer {rec}"})
    profile_row = (
        db_session.query(Embedding).filter(Embedding.owner_type == EmbeddingOwnerType.PROFILE.value).one()
    )
    job_row = (
        db_session.query(Embedding)
        .filter(Embedding.owner_type == EmbeddingOwnerType.JOB.value, Embedding.chunk_type == "full")
        .one()
    )
    denied = client.post(
        "/api/v1/admin/embeddings/similarity",
        headers={"Authorization": f"Bearer {token}"},
        json={"left_embedding_id": str(profile_row.id), "right_embedding_id": str(job_row.id)},
    )
    assert denied.status_code == 403
    admin = _admin_token(client, db_session, "emb-admin@example.com")
    ok = client.post(
        "/api/v1/admin/embeddings/similarity",
        headers={"Authorization": f"Bearer {admin}"},
        json={"left_embedding_id": str(profile_row.id), "right_embedding_id": str(job_row.id)},
    )
    assert ok.status_code == 200, ok.text
    assert "vector" not in ok.json()
    assert -1 <= ok.json()["similarity"] <= 1
    job_row.model_version = "other-version"
    db_session.flush()
    bad = client.post(
        "/api/v1/admin/embeddings/similarity",
        headers={"Authorization": f"Bearer {admin}"},
        json={"left_embedding_id": str(profile_row.id), "right_embedding_id": str(job_row.id)},
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "EMBEDDING_INCOMPATIBLE"


def test_pgvector_similarity_query(db_session: Session) -> None:
    encoder = HashingEncoder(dimensions=8)
    set_encoder(encoder)
    service = EmbeddingService(db_session, encoder=encoder)
    left = encoder.encode("alpha query")
    row = Embedding(
        owner_type=EmbeddingOwnerType.PROFILE.value,
        owner_id=uuid.uuid4(),
        chunk_type="full",
        model_name=encoder.model_name,
        model_version=encoder.model_version,
        embedding_text_version="embedding-text-v1",
        dimensions=8,
        content_hash=content_hash("alpha query"),
        vector=left,
    )
    db_session.add(row)
    db_session.flush()
    hits = service.similar_owners(query=left, owner_type=EmbeddingOwnerType.PROFILE.value, limit=5)
    assert hits
    assert hits[0][0].id == row.id
    assert hits[0][1] == pytest.approx(1.0, abs=1e-5)
    reset_encoder()


def test_job_requirement_text_keeps_raw_evidence_separate() -> None:
    from types import SimpleNamespace

    from app.modules.embeddings.text_builder import build_job_requirement_text

    skill = SimpleNamespace(canonical_name="Python")
    job = SimpleNamespace(title="Backend")
    requirement = SimpleNamespace(
        extracted_payload={
            "title": "Backend",
            "required_skills": [{"raw_text": "pythn"}],
            "preferred_skills": [],
        },
        required_skills=[SimpleNamespace(skill=skill)],
        preferred_skills=[],
        min_years_experience=None,
        education_level=None,
    )
    text = build_job_requirement_text(job, requirement)
    assert "Required skills: Python" in text
    assert "Unmatched requirement mentions: pythn" in text
    requirement.required_skills = []
    raw_only = build_job_requirement_text(job, requirement)
    assert "Required skills:" not in raw_only
    assert "Unmatched requirement mentions: pythn" in raw_only


def test_minilm_semantic_smoke() -> None:
    import os

    if os.environ.get("RUN_MINILM_TESTS") != "1":
        pytest.skip("Set RUN_MINILM_TESTS=1 to load MiniLM.")
    from app.modules.embeddings.encoder import SentenceTransformerEncoder

    try:
        encoder = SentenceTransformerEncoder(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_version="all-minilm-l6-v2-v1",
        )
    except Exception as exc:
        pytest.skip(f"MiniLM unavailable: {exc}")
    assert encoder.dimensions == 384
    text_a = "Developed machine learning models for classification and regression."
    text_b = "Built predictive models using Python for supervised learning."
    text_c = "Designed React user interfaces."
    vec_a = encoder.encode(text_a)
    vec_b = encoder.encode(text_b)
    vec_c = encoder.encode(text_c)
    ab = cosine_similarity(vec_a, vec_b)
    ac = cosine_similarity(vec_a, vec_c)
    assert ab > ac
    again = encoder.encode(text_a)
    assert cosine_similarity(vec_a, again) == pytest.approx(1.0, abs=1e-5)


def _candidate(client: TestClient, email: str):
    register_user(client, email=email, role="candidate")
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def _recruiter(client: TestClient, email: str, org: str):
    register_user(client, email=email, role="recruiter", organization_name=org)
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def _admin_token(client: TestClient, db_session: Session, email: str) -> str:
    db_session.add(
        User(
            email=email,
            password_hash=hash_password(PASSWORD),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    db_session.flush()
    return login_user(client, email=email)["_access"]


def _upload_and_confirm(
    client: TestClient, token: str, candidate_id: str, extra_line: str | None = None
) -> None:
    lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
    if extra_line:
        lines.append(extra_line)
    uploaded = client.post(
        f"/api/v1/candidates/{candidate_id}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    confirmed = client.post(
        f"/api/v1/candidates/{candidate_id}/profile/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirmed.status_code == 200, confirmed.text
