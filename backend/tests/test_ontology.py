from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CandidateSkill, JobRequiredSkill, Skill, User
from app.models.enums import UserRole, UserStatus
from app.modules.identity.password import hash_password
from app.modules.nlp.pipeline import extract_profile_draft
from app.modules.ontology.catalog import SEED_VERSION, SKILLS
from app.modules.ontology.normalize import normalize_lookup
from app.modules.ontology.policies import classify_relationship
from app.modules.ontology.seed import seed_ontology
from app.modules.ontology.service import OntologyService
from app.modules.ontology.validation import parent_cycles
from tests.auth_helpers import PASSWORD, login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_JD, ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines


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


def _skill_id(db_session: Session, slug: str):
    return db_session.query(Skill).filter(Skill.slug == slug).one().id


def test_seed_is_idempotent(db_session: Session) -> None:
    first = seed_ontology(db_session)
    second = seed_ontology(db_session)
    assert first.version == SEED_VERSION
    assert second.version == SEED_VERSION
    assert first.checksum == second.checksum
    assert db_session.query(Skill).count() == len(SKILLS)


def test_canonical_and_alias_resolution(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    ml = service.resolve_mention("Machine Learning")
    assert ml.resolution_type == "canonical"
    assert ml.canonical_skill_name == "Machine Learning"
    alias = service.resolve_mention("ML")
    assert alias.resolution_type == "alias"
    assert alias.canonical_skill_id == ml.canonical_skill_id
    spaced = service.resolve_mention(" Machine Learning ")
    hyphen = service.resolve_mention("machine-learning")
    assert spaced.canonical_skill_id == ml.canonical_skill_id
    assert hyphen.canonical_skill_id == ml.canonical_skill_id
    assert hyphen.resolution_type in {"alias", "canonical"}
    assert service.resolve_mention("AI").canonical_skill_name == "Artificial Intelligence"
    assert service.resolve_mention("NLP").canonical_skill_name == "Natural Language Processing"
    assert service.resolve_mention("JS").canonical_skill_name == "JavaScript"
    assert service.resolve_mention("TS").canonical_skill_name == "TypeScript"


def test_technical_syntax_preserved(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    assert service.resolve_mention("C++").canonical_skill_name == "C++"
    assert service.resolve_mention("C#").canonical_skill_name == "C#"
    assert service.resolve_mention(".NET").canonical_skill_name == ".NET"
    assert service.resolve_mention("Node.js").canonical_skill_name == "Node.js"
    assert service.resolve_mention("Next.js").canonical_skill_name == "Next.js"
    assert service.resolve_mention("CI/CD").canonical_skill_name == "CI/CD"
    assert "++" in normalize_lookup("C++")
    assert normalize_lookup("scikit-learn") == "scikit-learn"


def test_unknown_is_unmatched_and_not_invented(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    before = db_session.query(Skill).count()
    result = service.resolve_mention("QuantumFlow AI")
    assert result.resolution_type == "unmatched"
    assert result.needs_review is True
    assert result.canonical_skill_id is None
    assert db_session.query(Skill).count() == before


def test_fuzzy_threshold_and_ambiguity(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    close = service.resolve_mention("Machne Learning", fuzzy_threshold=0.85)
    assert close.resolution_type == "fuzzy"
    assert close.canonical_skill_name == "Machine Learning"
    assert close.needs_review is True
    weak = service.resolve_mention("zzzqqq", fuzzy_threshold=0.92)
    assert weak.resolution_type == "unmatched"


def test_hierarchy_policy(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    ml = _skill_id(db_session, "machine-learning")
    dl = _skill_id(db_session, "deep-learning")
    docker = _skill_id(db_session, "docker")
    kube = _skill_id(db_session, "kubernetes")
    child = service.classify(ml, dl)
    assert child.evidence_type == "child"
    parent = service.classify(dl, ml)
    assert parent.evidence_type == "parent"
    related = service.classify(kube, docker)
    assert related.evidence_type == "related"
    exact = service.classify(ml, ml)
    assert exact.evidence_type == "exact"
    graph = service.graph()
    assert graph is not None
    classified = classify_relationship(
        graph,
        job_skill_id=ml,
        job_skill_name="Machine Learning",
        candidate_skill_id=dl,
        candidate_skill_name="Deep Learning",
        ontology_version=SEED_VERSION,
    )
    assert classified.evidence_type == "child"


def test_parent_cycles_rejected(db_session: Session, seeded_ontology) -> None:
    a = _skill_id(db_session, "python")
    b = _skill_id(db_session, "java")
    c = _skill_id(db_session, "go")
    errors = parent_cycles([(a, b), (b, c), (c, a)])
    assert errors


def test_snapshot_is_immutable_until_new_version(db_session: Session, seeded_ontology) -> None:
    service = OntologyService(db_session)
    admin = User(
        email="ont-admin@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(admin)
    db_session.flush()
    ml = service.resolve_mention("ML")
    from app.modules.ontology.schemas import AliasCreate, VersionCreate

    service.create_alias(
        admin,
        AliasCreate(skill_id=ml.canonical_skill_id, alias="ml-extra-alias-xyz"),
    )
    still = service.resolve_mention("ml-extra-alias-xyz")
    assert still.resolution_type == "unmatched"
    service.create_version(admin, VersionCreate(version="seed-0.2", activate=True))
    now = service.resolve_mention("ml-extra-alias-xyz")
    assert now.canonical_skill_name == "Machine Learning"
    assert now.ontology_version == "seed-0.2"


def test_admin_only_mutation(client: TestClient, db_session: Session, seeded_ontology) -> None:
    token, _ = _candidate(client, "ont-cand@example.com")
    denied = client.post(
        "/api/v1/admin/ontology/skills",
        headers={"Authorization": f"Bearer {token}"},
        json={"canonical_name": "Forbidden Skill"},
    )
    assert denied.status_code == 403
    rec_token, _ = _recruiter(client, "ont-rec@example.com")
    denied_rec = client.get(
        "/api/v1/admin/ontology/skills",
        headers={"Authorization": f"Bearer {rec_token}"},
    )
    assert denied_rec.status_code == 403
    admin = _admin_token(client, db_session, "ont-real-admin@example.com")
    created = client.post(
        "/api/v1/admin/ontology/skills",
        headers={"Authorization": f"Bearer {admin}"},
        json={"canonical_name": "GraphQL", "category": "Web Development"},
    )
    assert created.status_code == 200, created.text
    listed = client.get("/api/v1/admin/ontology/skills", headers={"Authorization": f"Bearer {admin}"})
    names = [item["canonical_name"] for item in listed.json()["items"]]
    assert "GraphQL" in names
    versions = client.get("/api/v1/admin/ontology/versions", headers={"Authorization": f"Bearer {admin}"})
    assert versions.status_code == 200
    assert any(item["version"] == SEED_VERSION for item in versions.json())


def test_resume_and_job_share_canonical_ids(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    token, user = _candidate(client, "ont-up@example.com")
    cid = user["candidate_id"]
    lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
    uploaded = client.post(
        f"/api/v1/candidates/{cid}/resumes",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    profile = client.get(
        f"/api/v1/candidates/{cid}/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    body = profile.json()["draft"]
    assert body["ontology_version"] == SEED_VERSION
    normalized = body["normalized_skills"]
    by_raw = {item["raw_text"].upper(): item for item in normalized}
    assert by_raw["ML"]["canonical_skill_name"] == "Machine Learning"
    assert by_raw["ML"]["resolution_type"] == "alias"
    machine = next(item for item in normalized if item["raw_text"].casefold() == "machine learning")
    assert machine["canonical_skill_id"] == by_raw["ML"]["canonical_skill_id"]
    python = next(item for item in normalized if item["raw_text"].casefold() == "python")
    assert python["resolution_type"] == "canonical"
    client.post(f"/api/v1/candidates/{cid}/profile/confirm", headers={"Authorization": f"Bearer {token}"})
    db_session.expire_all()
    stored = db_session.query(CandidateSkill).all()
    skill_ids = [row.skill_id for row in stored]
    assert len(skill_ids) == len(set(skill_ids))
    assert stored
    rec_token, _ = _recruiter(client, "ont-jd@example.com")
    job = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {rec_token}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    assert job.status_code == 201, job.text
    req = job.json()["requirements"]
    assert req["ontology_version"] == SEED_VERSION
    required = {
        item["canonical_skill_name"]: item["canonical_skill_id"]
        for item in req["normalized_required_skills"]
    }
    assert "Python" in required
    python_job = required["Python"]
    python_cand = python["canonical_skill_id"]
    assert str(python_job) == str(python_cand)
    client.post(
        f"/api/v1/jobs/{job.json()['id']}/requirements/confirm",
        headers={"Authorization": f"Bearer {rec_token}"},
    )
    db_session.expire_all()
    assert db_session.query(JobRequiredSkill).count() >= 1


def test_nlp_raw_mentions_still_distinct() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    raw = {item.raw_text for item in draft.skills}
    assert any(value.upper() == "ML" for value in raw)
    assert any(value.casefold() == "machine learning" for value in raw)


def _candidate(client: TestClient, email: str):
    register_user(client, email=email, role="candidate")
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def _recruiter(client: TestClient, email: str):
    register_user(client, email=email, role="recruiter", organization_name="Ontology Corp")
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]
