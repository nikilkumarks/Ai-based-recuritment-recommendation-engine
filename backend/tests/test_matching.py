from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    CandidateSkill,
    Embedding,
    FeatureSnapshot,
    MatchExplanation,
    MatchRun,
    Skill,
    User,
)
from app.models.enums import UserRole, UserStatus
from app.modules.identity.password import hash_password
from app.modules.matching.composer import compose
from app.modules.matching.constants import RELATED_REQUIRED_CREDIT
from app.modules.matching.evidence import SkillRef, collect_required_evidence
from app.modules.matching.policies import default_scoring_policy
from app.modules.ontology.graph import SkillGraph
from tests.auth_helpers import PASSWORD, login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines

SCENARIO_JD = """
Machine learning engineer role.
Required skills: Machine Learning, Python, and Kubernetes.
Preferred: Docker.
Minimum 3 years of experience. Education: bachelor.
""".strip()


def test_composer_score_range_and_reconstruction() -> None:
    policy = default_scoring_policy()
    features = {
        "required_skill_count": 3,
        "matched_required_skill_count": 2,
        "preferred_skill_count": 1,
        "matched_preferred_skill_count": 1,
        "semantic_similarity_available": True,
        "profile_job_cosine": 0.8,
        "required_experience_years": 3,
        "candidate_experience_years": 4,
        "education_requirement_present": False,
        "education_alignment": None,
        "candidate_project_count": 0,
        "relevant_project_count": 0,
        "project_evidence_present": False,
    }
    result = compose(features, policy)
    assert 0.0 <= result.current_match <= 1.0
    again = compose(features, policy)
    assert again.current_match == result.current_match
    expected = (
        (2 / 3) * 0.60
        + 1.0 * 0.10
        + 0.8 * 0.15
        + 1.0 * 0.10
        + 1.0 * 0.05
    )
    assert result.current_match == pytest.approx(round(expected, 4))
    assert RELATED_REQUIRED_CREDIT == 0.0


def test_required_skills_dominate_semantic() -> None:
    policy = default_scoring_policy()
    features = {
        "required_skill_count": 3,
        "matched_required_skill_count": 0,
        "preferred_skill_count": 0,
        "matched_preferred_skill_count": 0,
        "semantic_similarity_available": True,
        "profile_job_cosine": 0.99,
        "required_experience_years": None,
        "candidate_experience_years": None,
        "education_requirement_present": False,
        "candidate_project_count": 0,
        "relevant_project_count": 0,
        "project_evidence_present": False,
    }
    result = compose(features, policy)
    assert result.current_match <= 0.40 + 1e-6


def test_missing_semantic_renormalizes() -> None:
    policy = default_scoring_policy()
    features = {
        "required_skill_count": 2,
        "matched_required_skill_count": 2,
        "preferred_skill_count": 0,
        "matched_preferred_skill_count": 0,
        "semantic_similarity_available": False,
        "profile_job_cosine": None,
        "required_experience_years": None,
        "candidate_experience_years": None,
        "education_requirement_present": False,
        "candidate_project_count": 0,
        "relevant_project_count": 0,
        "project_evidence_present": False,
    }
    result = compose(features, policy)
    semantic = next(item for item in result.components if item.name == "semantic")
    assert semantic.available is False
    assert result.used_weight_sum == pytest.approx(0.85)
    assert result.current_match == pytest.approx(1.0)


def test_unknown_experience_does_not_fail() -> None:
    policy = default_scoring_policy()
    features = {
        "required_skill_count": 1,
        "matched_required_skill_count": 1,
        "preferred_skill_count": 0,
        "matched_preferred_skill_count": 0,
        "semantic_similarity_available": False,
        "required_experience_years": 3,
        "candidate_experience_years": None,
        "education_requirement_present": True,
        "education_alignment": None,
        "candidate_project_count": 0,
        "relevant_project_count": 0,
        "project_evidence_present": False,
    }
    result = compose(features, policy)
    experience = next(item for item in result.components if item.name == "experience")
    assert experience.value == 1.0
    education = next(item for item in result.components if item.name == "education_project")
    assert education.value == 1.0


def test_ontology_evidence_kinds() -> None:
    ml, dl, python, k8s, docker = (uuid.uuid4() for _ in range(5))
    graph = SkillGraph(
        children={ml: (dl,)},
        parents={dl: (ml,)},
        related={k8s: (docker,), docker: (k8s,)},
        max_depth=4,
    )
    candidate = [
        SkillRef(ml, "Machine Learning", mention="ML", resolution_type="alias"),
        SkillRef(python, "Python", mention="Python", resolution_type="canonical"),
        SkillRef(docker, "Docker", mention="Docker", resolution_type="canonical"),
        SkillRef(ml, "Machine Learning", mention="Machine Learning", resolution_type="canonical"),
    ]
    required = [
        SkillRef(ml, "Machine Learning"),
        SkillRef(python, "Python"),
        SkillRef(k8s, "Kubernetes"),
        SkillRef(dl, "Deep Learning"),
    ]
    evidence = collect_required_evidence(
        graph,
        required=required,
        candidate_skills=candidate,
        ontology_version="seed-0.1",
    )
    kinds = {item.job_skill_name: item.kind for item in evidence}
    assert kinds["Machine Learning"] == "exact"
    assert kinds["Python"] == "exact"
    assert kinds["Kubernetes"] == "related"
    assert kinds["Deep Learning"] == "parent"
    ml_item = next(item for item in evidence if item.job_skill_name == "Machine Learning")
    assert ml_item.via_alias is True
    child = collect_required_evidence(
        graph,
        required=[SkillRef(ml, "Machine Learning")],
        candidate_skills=[SkillRef(dl, "Deep Learning")],
        ontology_version="seed-0.1",
    )
    assert child[0].kind == "child"
    missing = collect_required_evidence(
        graph,
        required=[SkillRef(k8s, "Kubernetes")],
        candidate_skills=[SkillRef(python, "Python")],
        ontology_version="seed-0.1",
    )
    assert missing[0].kind == "missing"


def test_scenario_alias_related_preferred(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user, rec_token, job_id = _scenario_pair(client)
    cid = cand_user["candidate_id"]
    match = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    )
    assert match.status_code == 200, match.text
    body = match.json()
    assert body["scoring_mode"] == "baseline"
    assert body["model_version"] is None
    assert body["potential"] is not None
    assert body["potential_status"] == "available"
    assert 0.0 <= body["potential"] <= 1.0
    assert body["feature_schema_version"] == "feature-schema-v2"
    assert body["ontology_version"] == "seed-0.1"
    assert body["required_skill_coverage"] == pytest.approx(2 / 3, abs=1e-4)
    assert body["preferred_skill_coverage"] == pytest.approx(1.0)
    matched = {item["skill"] for item in body["matched_skills"]}
    missing = {item["skill"] for item in body["missing_skills"]}
    related = {item["skill"] for item in body["related_skills"]}
    assert "Machine Learning" in matched
    assert "Python" in matched
    assert "Kubernetes" not in matched
    assert "Kubernetes" not in missing
    assert "Kubernetes" in related
    traces = {item["type"] for item in body["explanations"]}
    assert "alias_match" in traces
    assert "related_skill" in traces
    assert "preferred_skill" in traces
    k8s_related = next(item for item in body["related_skills"] if item["skill"] == "Kubernetes")
    assert k8s_related["candidate_evidence"] == "Docker"
    gaps = {item["skill"]: item["type"] for item in body["gaps"]}
    assert gaps.get("Kubernetes") == "related"
    adjacent = next(
        item
        for item in body["explanations"]
        if item["type"] == "potential_adjacent" and item.get("missing_skill") == "Kubernetes"
    )
    assert adjacent["candidate_skill"] == "Docker"
    assert adjacent["relation"] == "related_to"
    assert adjacent["distance"] == 1
    assert body["suggested_skill_paths"]
    db_session.expire_all()
    runs = (
        db_session.query(MatchRun)
        .filter(MatchRun.candidate_id == uuid.UUID(cid), MatchRun.job_id == uuid.UUID(job_id))
        .all()
    )
    assert runs
    run = runs[-1]
    assert run.potential is not None
    assert run.scoring_mode == "baseline"
    assert run.model_version is None
    snap = db_session.query(FeatureSnapshot).filter(FeatureSnapshot.match_run_id == run.id).one()
    assert snap.feature_schema_version == "feature-schema-v2"
    assert snap.features["matched_required_skill_count"] == 2
    assert snap.features["required_skill_count"] == 3
    assert snap.features["matched_preferred_skill_count"] == 1
    reconstructed = compose(snap.features, default_scoring_policy())
    assert reconstructed.current_match == pytest.approx(body["current_match"])
    assert body["current_match"] == pytest.approx(reconstructed.current_match)
    assert snap.features.get("potential") == pytest.approx(body["potential"])
    explanation = db_session.query(MatchExplanation).filter(MatchExplanation.match_run_id == run.id).one()
    assert explanation.traces


def test_child_parent_relationships(client: TestClient, seeded_ontology) -> None:
    cand_token, cand_user = _candidate(client, "child-parent@example.com")
    rec_token, _ = _recruiter(client, "child-parent-rec@example.com", "Hierarchy Corp")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={"skills": [_mention("Deep Learning")]},
    )
    _confirm_profile(client, cand_token, cid)
    job_ml = _job_with_skills(
        client,
        rec_token,
        "ML role needing machine learning skills now.",
        ["Machine Learning"],
        [],
    )
    job_dl = _job_with_skills(
        client,
        rec_token,
        "DL role needing deep learning skills today.",
        ["Deep Learning"],
        [],
    )
    child = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_ml}/match",
        headers=_bearer(cand_token),
    ).json()
    assert child["partial_skills"][0]["evidence_type"] == "child"
    assert child["required_skill_coverage"] == 0
    # New candidate with parent skill for the DL job.
    cand2, user2 = _candidate(client, "parent-skill@example.com")
    _upload_draft(client, cand2, user2["candidate_id"])
    client.put(
        f"/api/v1/candidates/{user2['candidate_id']}/profile",
        headers=_bearer(cand2),
        json={"skills": [_mention("Machine Learning")]},
    )
    _confirm_profile(client, cand2, user2["candidate_id"])
    parent = client.get(
        f"/api/v1/candidates/{user2['candidate_id']}/jobs/{job_dl}/match",
        headers=_bearer(cand2),
    ).json()
    assert parent["partial_skills"][0]["evidence_type"] == "parent"
    assert parent["required_skill_coverage"] == 0


def test_semantic_and_embedding_fallbacks(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user, rec_token, job_id = _scenario_pair(client)
    cid = cand_user["candidate_id"]
    missing = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert missing["semantic_similarity_available"] is False
    assert missing["semantic_similarity"] is None
    assert client.post(
        f"/api/v1/candidates/{cid}/profile/embedding",
        headers=_bearer(cand_token),
    ).status_code == 200
    assert client.post(
        f"/api/v1/jobs/{job_id}/embedding",
        headers=_bearer(rec_token),
    ).status_code == 200
    current = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert current["semantic_similarity_available"] is True
    assert current["semantic_similarity"] is not None
    first = current["current_match"]
    second = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert second["current_match"] == first
    db_session.expire_all()
    from app.models import CandidateProfile

    confirmed = (
        db_session.query(CandidateProfile)
        .filter(CandidateProfile.candidate_id == uuid.UUID(cid))
        .order_by(CandidateProfile.profile_version.desc())
        .first()
    )
    assert confirmed is not None
    row = (
        db_session.query(Embedding)
        .filter(Embedding.owner_id == confirmed.id)
        .order_by(Embedding.created_at.desc())
        .first()
    )
    assert row is not None
    row.content_hash = "0" * 64
    db_session.flush()
    stale = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert stale["semantic_similarity_available"] is False
    row.model_name = "other-encoder"
    row.content_hash = "1" * 64
    db_session.flush()
    incompatible = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert incompatible["semantic_similarity_available"] is False


def test_experience_education_project_policies(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user = _candidate(client, "exp-edu@example.com")
    rec_token, _ = _recruiter(client, "exp-edu-rec@example.com", "Exp Corp")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={
            "skills": [_mention("Python")],
            "experience": [
                {
                    "job_title": "Engineer",
                    "years_experience": 4,
                    "employer": "Acme",
                }
            ],
            "education": [
                {
                    "institution": "NIT",
                    "education_level": "bachelor",
                }
            ],
            "projects": [
                {
                    "name": "House Price Prediction using regression",
                    "description": "Machine learning prediction project",
                }
            ],
        },
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "Python engineer needing python skills and bachelor education.",
        ["Python"],
        [],
        min_years=3,
        education="bachelor",
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    traces = {item["type"] for item in body["explanations"]}
    assert "experience_match" in traces
    assert "education_match" in traces
    job_gap = _job_with_skills(
        client,
        rec_token,
        "Senior python role requiring python and many years now.",
        ["Python"],
        [],
        min_years=10,
    )
    gap = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_gap}/match",
        headers=_bearer(cand_token),
    ).json()
    assert any(item["type"] == "experience_gap" for item in gap["explanations"])
    unknown_token, unknown_user = _candidate(client, "unknown-years@example.com")
    _upload_draft(client, unknown_token, unknown_user["candidate_id"])
    client.put(
        f"/api/v1/candidates/{unknown_user['candidate_id']}/profile",
        headers=_bearer(unknown_token),
        json={
            "skills": [_mention("Python")],
            "experience": [{"job_title": "Engineer", "employer": "Acme"}],
        },
    )
    _confirm_profile(client, unknown_token, unknown_user["candidate_id"])
    unknown = client.get(
        f"/api/v1/candidates/{unknown_user['candidate_id']}/jobs/{job_id}/match",
        headers=_bearer(unknown_token),
    ).json()
    assert any(item["type"] == "experience_unknown" for item in unknown["explanations"])
    no_edu = _job_with_skills(
        client,
        rec_token,
        "Python role with no education bar for this listing.",
        ["Python"],
        [],
    )
    none_req = client.get(
        f"/api/v1/candidates/{cid}/jobs/{no_edu}/match",
        headers=_bearer(cand_token),
    ).json()
    assert none_req["required_skill_coverage"] == 1.0
    db_session.expire_all()
    from app.models import CandidateProfile, ProjectItem

    profile = (
        db_session.query(CandidateProfile)
        .filter(CandidateProfile.candidate_id == uuid.UUID(cid))
        .order_by(CandidateProfile.profile_version.desc())
        .first()
    )
    assert profile is not None
    project = db_session.query(ProjectItem).filter(ProjectItem.candidate_profile_id == profile.id).first()
    assert project is not None
    client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers=_bearer(cand_token))
    client.post(f"/api/v1/jobs/{job_id}/embedding", headers=_bearer(rec_token))
    db_session.expire_all()
    job_emb = (
        db_session.query(Embedding)
        .filter(Embedding.owner_id == uuid.UUID(job_id))
        .order_by(Embedding.created_at.desc())
        .first()
    )
    project_emb = (
        db_session.query(Embedding)
        .filter(Embedding.owner_id == project.id)
        .order_by(Embedding.created_at.desc())
        .first()
    )
    assert job_emb is not None
    if project_emb is not None:
        project_emb.vector = list(job_emb.vector)
        db_session.flush()
        evidenced = client.get(
            f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
            headers=_bearer(cand_token),
        ).json()
        assert any(item["type"] == "project_evidence" for item in evidenced["explanations"])


def test_counterfactual_does_not_modify_db(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user, rec_token, job_id = _scenario_pair(client)
    cid = cand_user["candidate_id"]
    k8s = db_session.query(Skill).filter(Skill.slug == "kubernetes").one()
    before = (
        db_session.query(CandidateSkill)
        .join(CandidateSkill.profile)
        .filter(CandidateSkill.skill_id == k8s.id)
        .count()
    )
    runs_before = db_session.query(MatchRun).count()
    response = client.post(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/counterfactual",
        headers=_bearer(cand_token),
        json={"skill_id": str(k8s.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["persisted"] is False
    assert body["delta"] > 0
    assert body["simulated_current_match"] > body["baseline_current_match"]
    assert body["potential_before"] is not None
    assert body["potential_after"] is None
    assert body["scoring_mode"] == "baseline"
    assert body["model_version"] is None
    db_session.expire_all()
    after = (
        db_session.query(CandidateSkill)
        .join(CandidateSkill.profile)
        .filter(CandidateSkill.skill_id == k8s.id)
        .count()
    )
    assert after == before
    assert db_session.query(MatchRun).count() == runs_before


def test_candidate_authorization_and_two_way(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user, rec_token, job_id = _scenario_pair(client)
    cid = cand_user["candidate_id"]
    candidate_row = db_session.query(Candidate).filter(Candidate.id == uuid.UUID(cid)).one()
    candidate_row.preferences = {"discoverable": True}
    db_session.flush()
    other_token, _ = _candidate(client, "other-match@example.com")
    denied = client.get(
        f"/api/v1/candidates/{cid}/jobs",
        headers=_bearer(other_token),
    )
    assert denied.status_code == 403
    listed = client.get(f"/api/v1/candidates/{cid}/jobs", headers=_bearer(cand_token))
    assert listed.status_code == 200, listed.text
    assert listed.json()["scoring_mode"] == "baseline"
    assert listed.json()["items"]
    rec_list = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=_bearer(rec_token))
    assert rec_list.status_code == 200, rec_list.text
    payload = rec_list.json()
    assert payload["sort"].startswith("current_match DESC")
    assert payload["scoring_mode"] == "baseline"
    scores = [item["current_match"] for item in payload["items"]]
    assert scores == sorted(scores, reverse=True)
    other_rec, _ = _recruiter(client, "foreign-match@example.com", "Foreign Match Org")
    isolated = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=_bearer(other_rec))
    assert isolated.status_code == 403
    candidate_row.preferences = {}
    db_session.flush()
    hidden_list = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=_bearer(rec_token))
    assert hidden_list.status_code == 200
    assert hidden_list.json()["items"] == []
    candidate_row.preferences = {"discoverable": True}
    db_session.flush()
    visible = client.get(f"/api/v1/jobs/{job_id}/candidates", headers=_bearer(rec_token))
    assert any(item["candidate_id"] == cid for item in visible.json()["items"])
    db_session.add(
        User(
            email="match-admin@example.com",
            password_hash=hash_password(PASSWORD),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    db_session.flush()
    admin = login_user(client, email="match-admin@example.com")["_access"]
    diagnostic = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(admin),
    )
    assert diagnostic.status_code == 200


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mention(text: str) -> dict[str, str]:
    return {"raw_text": text, "normalized_text": text.lower(), "evidence": text}


def _candidate(client: TestClient, email: str):
    register_user(client, email=email, role="candidate")
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def _recruiter(client: TestClient, email: str, org: str):
    register_user(client, email=email, role="recruiter", organization_name=org)
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def _upload_draft(client: TestClient, token: str, candidate_id: str) -> None:
    lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
    uploaded = client.post(
        f"/api/v1/candidates/{candidate_id}/resumes",
        headers=_bearer(token),
        files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text


def _confirm_profile(client: TestClient, token: str, candidate_id: str) -> None:
    confirmed = client.post(
        f"/api/v1/candidates/{candidate_id}/profile/confirm",
        headers=_bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text


def _job_with_skills(
    client: TestClient,
    token: str,
    description: str,
    required: list[str],
    preferred: list[str],
    min_years: float | None = None,
    education: str | None = None,
) -> str:
    created = client.post(
        "/api/v1/jobs",
        headers=_bearer(token),
        json={"title": "Engineer", "description_raw": description},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    payload: dict = {
        "required_skills": [_mention(name) for name in required],
        "preferred_skills": [_mention(name) for name in preferred],
    }
    if min_years is not None:
        payload["min_years_experience"] = min_years
    if education is not None:
        payload["education_level"] = education
    updated = client.put(
        f"/api/v1/jobs/{job_id}/requirements",
        headers=_bearer(token),
        json=payload,
    )
    assert updated.status_code == 200, updated.text
    confirmed = client.post(
        f"/api/v1/jobs/{job_id}/requirements/confirm",
        headers=_bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text
    return job_id


def _scenario_pair(client: TestClient):
    cand_token, cand_user = _candidate(client, f"scenario-{uuid.uuid4().hex[:8]}@example.com")
    rec_token, _ = _recruiter(
        client,
        f"scenario-rec-{uuid.uuid4().hex[:8]}@example.com",
        f"Org {uuid.uuid4().hex[:6]}",
    )
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={"skills": [_mention("ML"), _mention("Python"), _mention("Docker")]},
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        SCENARIO_JD,
        ["Machine Learning", "Python", "Kubernetes"],
        ["Docker"],
        min_years=3,
        education="bachelor",
    )
    return cand_token, cand_user, rec_token, job_id
