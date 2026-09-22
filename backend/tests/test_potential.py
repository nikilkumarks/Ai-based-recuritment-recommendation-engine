"""Phase 8 heuristic potential and suggested skill paths. Not hiring probability."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateSkill, FeatureSnapshot, MatchExplanation, MatchRun, Skill
from app.modules.matching.composer import compose
from app.modules.matching.evidence import SkillEvidence, SkillRef, collect_required_evidence
from app.modules.matching.policies import default_scoring_policy
from app.modules.matching.potential import assess_potential, default_potential_policy
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.resolver import OntologyIndex, SkillRecord
from tests.test_matching import (
    _bearer,
    _candidate,
    _confirm_profile,
    _job_with_skills,
    _mention,
    _recruiter,
    _scenario_pair,
    _upload_draft,
)


def _record(skill_id: uuid.UUID, name: str) -> SkillRecord:
    return SkillRecord(
        id=skill_id,
        canonical_name=name,
        slug=name.lower().replace(" ", "-"),
        status="active",
        lookup=name.lower(),
    )


def _index(
    names: dict[uuid.UUID, str],
    *,
    children: dict[uuid.UUID, tuple[uuid.UUID, ...]] | None = None,
    parents: dict[uuid.UUID, tuple[uuid.UUID, ...]] | None = None,
    related: dict[uuid.UUID, tuple[uuid.UUID, ...]] | None = None,
) -> OntologyIndex:
    return OntologyIndex(
        version="seed-0.1",
        checksum="test",
        skills={skill_id: _record(skill_id, name) for skill_id, name in names.items()},
        canonical_lookup={},
        exact_alias={},
        normalized_alias={},
        children=children or {},
        parents=parents or {},
        related=related or {},
        similar={},
    )


def _profile(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(
        project_items=list(kwargs.get("project_items") or []),
        experience_items=list(kwargs.get("experience_items") or []),
        certification_items=list(kwargs.get("certification_items") or []),
    )


def _evidence(
    job_id: uuid.UUID,
    job_name: str,
    kind: str,
    *,
    candidate_id: uuid.UUID | None = None,
    candidate_name: str | None = None,
    hops: int | None = None,
) -> SkillEvidence:
    return SkillEvidence(
        job_skill_id=job_id,
        job_skill_name=job_name,
        kind=kind,  # type: ignore[arg-type]
        candidate_skill_id=candidate_id,
        candidate_skill_name=candidate_name,
        candidate_mention=candidate_name,
        hops=hops,
        via_alias=False,
    )


def test_graph_distance_max_depth_and_cycles() -> None:
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    graph = SkillGraph(
        children={},
        parents={},
        related={a: (b,), b: (a, c), c: (b, d), d: (c,)},
        similar={},
        max_depth=2,
    )
    assert graph.shortest_path(a, b) == [a, b]
    assert graph.shortest_path(a, c) == [a, b, c]
    assert graph.shortest_path(a, d) is None
    cyclic = SkillGraph(
        children={},
        parents={},
        related={a: (b, a), b: (a, b)},
        similar={},
        max_depth=8,
    )
    assert cyclic.shortest_path(a, b) == [a, b]


def test_related_child_parent_weights_and_adjacent_ratio() -> None:
    docker, k8s, ml, dl, python = (uuid.uuid4() for _ in range(5))
    names = {
        docker: "Docker",
        k8s: "Kubernetes",
        ml: "Machine Learning",
        dl: "Deep Learning",
        python: "Python",
    }
    index = _index(
        names,
        children={ml: (dl,)},
        parents={dl: (ml,)},
        related={docker: (k8s,), k8s: (docker,)},
    )
    graph = index.graph(2)
    policy = default_potential_policy()
    related = assess_potential(
        graph=graph,
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(k8s, "Kubernetes", "related", candidate_id=docker, candidate_name="Docker", hops=1)
        ],
        preferred=[],
        candidate_skills=[SkillRef(docker, "Docker")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert related.status == "available"
    assert related.potential is not None
    assert 0.0 <= related.potential <= 1.0
    assert related.adjacent_skill_ratio == 1.0
    assert related.gaps[0].graph_score == pytest.approx(policy.related)
    child = assess_potential(
        graph=graph,
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(
                ml,
                "Machine Learning",
                "child",
                candidate_id=dl,
                candidate_name="Deep Learning",
                hops=1,
            )
        ],
        preferred=[],
        candidate_skills=[SkillRef(dl, "Deep Learning")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    parent = assess_potential(
        graph=graph,
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(
                dl,
                "Deep Learning",
                "parent",
                candidate_id=ml,
                candidate_name="Machine Learning",
                hops=1,
            )
        ],
        preferred=[],
        candidate_skills=[SkillRef(ml, "Machine Learning")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert child.gaps[0].graph_score == pytest.approx(policy.child)
    assert parent.gaps[0].graph_score == pytest.approx(policy.parent)
    assert child.gaps[0].graph_score > parent.gaps[0].graph_score
    three = assess_potential(
        graph=graph,
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(k8s, "Kubernetes", "related", candidate_id=docker, candidate_name="Docker", hops=1),
            _evidence(ml, "Machine Learning", "missing"),
            _evidence(python, "Python", "missing"),
        ],
        preferred=[],
        candidate_skills=[SkillRef(docker, "Docker")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert three.adjacent_skill_ratio == pytest.approx(1 / 3, abs=1e-4)


def test_missing_data_and_complete_match_policy() -> None:
    k8s, docker = uuid.uuid4(), uuid.uuid4()
    index = _index(
        {k8s: "Kubernetes", docker: "Docker"},
        related={k8s: (docker,), docker: (k8s,)},
    )
    policy = default_potential_policy()
    missing_projects = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(k8s, "Kubernetes", "related", candidate_id=docker, candidate_name="Docker", hops=1)
        ],
        preferred=[],
        candidate_skills=[SkillRef(docker, "Docker")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert missing_projects.features["potential_project_evidence"] is None
    assert missing_projects.features["potential_experience_evidence"] is None
    assert missing_projects.features["potential_certification_evidence"] is None
    assert missing_projects.features["potential_semantic_evidence"] is None
    complete = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(
                docker,
                "Docker",
                "exact",
                candidate_id=docker,
                candidate_name="Docker",
                hops=0,
            )
        ],
        preferred=[],
        candidate_skills=[SkillRef(docker, "Docker")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert complete.status == "not_applicable"
    assert complete.potential is None


def test_project_experience_cert_semantic_heuristics() -> None:
    cv, ml, opencv = (uuid.uuid4() for _ in range(3))
    index = _index(
        {cv: "Computer Vision", ml: "Machine Learning", opencv: "OpenCV"},
        related={cv: (ml, opencv), ml: (cv,), opencv: (cv,)},
    )
    policy = default_potential_policy()
    required = [
        _evidence(
            cv,
            "Computer Vision",
            "related",
            candidate_id=ml,
            candidate_name="Machine Learning",
            hops=1,
        )
    ]
    skills = [SkillRef(ml, "Machine Learning")]
    project = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(
            project_items=[
                SimpleNamespace(
                    name="Object Detection System",
                    description="Object Detection using OpenCV",
                    start_date=None,
                    end_date=None,
                )
            ]
        ),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert project.features["potential_project_evidence"] is not None
    assert any(item["type"] == "potential_project" for item in project.traces)
    assert any(item.get("evidence") == "OpenCV" for item in project.traces)
    experience = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(
            experience_items=[
                SimpleNamespace(
                    job_title="ML Engineer",
                    employer="Acme",
                    description="Built computer vision pipelines",
                    start_date=None,
                    end_date=None,
                )
            ]
        ),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert experience.features["potential_experience_evidence"] is not None
    cert_hit = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(
            certification_items=[
                SimpleNamespace(
                    name="Computer Vision Certificate",
                    issuing_organization="X",
                    issue_date=None,
                )
            ]
        ),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    cert_generic = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(
            certification_items=[
                SimpleNamespace(name="AWS Cloud Practitioner", issuing_organization="AWS", issue_date=None)
            ]
        ),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert cert_hit.features["potential_certification_evidence"]
    assert cert_generic.features["potential_certification_evidence"] == 0.0
    semantic = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": True, "profile_job_cosine": 0.7},
    )
    below = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": True, "profile_job_cosine": 0.1},
    )
    assert semantic.features["potential_semantic_evidence"] == pytest.approx(0.7)
    assert below.features["potential_semantic_evidence"] == 0.0
    first = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    second = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=required,
        preferred=[],
        candidate_skills=skills,
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert first.potential == second.potential


def test_required_gaps_dominate_preferred() -> None:
    ml, python, k8s, docker, html = (uuid.uuid4() for _ in range(5))
    index = _index(
        {
            ml: "Machine Learning",
            python: "Python",
            k8s: "Kubernetes",
            docker: "Docker",
            html: "HTML",
        },
        related={docker: (k8s,), k8s: (docker,)},
    )
    policy = default_potential_policy()
    result = assess_potential(
        graph=index.graph(2),
        index=index,
        ontology_version="seed-0.1",
        required=[
            _evidence(ml, "Machine Learning", "missing"),
            _evidence(python, "Python", "missing"),
            _evidence(k8s, "Kubernetes", "related", candidate_id=docker, candidate_name="Docker", hops=1),
        ],
        preferred=[
            _evidence(docker, "Docker", "exact", candidate_id=docker, candidate_name="Docker", hops=0),
        ],
        candidate_skills=[SkillRef(docker, "Docker"), SkillRef(html, "HTML")],
        profile=_profile(),
        policy=policy,
        semantic={"semantic_similarity_available": False},
    )
    assert result.gaps[0].required is True
    assert result.features["potential_graph_closability"] < policy.related


def test_related_skill_does_not_become_current_match() -> None:
    docker, k8s = uuid.uuid4(), uuid.uuid4()
    graph = SkillGraph(
        children={},
        parents={},
        related={docker: (k8s,), k8s: (docker,)},
        similar={},
        max_depth=4,
    )
    evidence = collect_required_evidence(
        graph,
        required=[SkillRef(k8s, "Kubernetes")],
        candidate_skills=[SkillRef(docker, "Docker")],
        ontology_version="seed-0.1",
    )
    assert evidence[0].kind == "related"
    features = {
        "required_skill_count": 1,
        "matched_required_skill_count": 0,
        "preferred_skill_count": 0,
        "matched_preferred_skill_count": 0,
        "semantic_similarity_available": False,
        "profile_job_cosine": None,
        "required_experience_years": None,
        "candidate_experience_years": None,
        "education_requirement_present": False,
        "education_alignment": None,
        "relevant_project_count": 0,
        "project_evidence_present": False,
    }
    current = compose(features, default_scoring_policy()).current_match
    potential = assess_potential(
        graph=graph,
        index=_index({docker: "Docker", k8s: "Kubernetes"}, related={docker: (k8s,), k8s: (docker,)}),
        ontology_version="seed-0.1",
        required=evidence,
        preferred=[],
        candidate_skills=[SkillRef(docker, "Docker")],
        profile=_profile(),
        policy=default_potential_policy(),
        semantic={"semantic_similarity_available": False},
    )
    assert potential.potential is not None
    assert current == compose(features, default_scoring_policy()).current_match


def test_phase8_scenario_and_career_authorization(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user, rec_token, job_id = _scenario_pair(client)
    cid = cand_user["candidate_id"]
    candidate_row = db_session.query(Candidate).filter(Candidate.id == uuid.UUID(cid)).one()
    candidate_row.preferences = {"discoverable": True}
    db_session.flush()
    match = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    )
    assert match.status_code == 200, match.text
    body = match.json()
    assert body["potential_status"] == "available"
    assert body["potential"] is not None
    assert body["potential"] != body["current_match"]
    assert 0.0 <= body["potential"] <= 1.0
    assert body["scoring_mode"] == "baseline"
    assert body["model_version"] is None
    paths = body["suggested_skill_paths"]
    assert any(item["target_skill"] == "Kubernetes" for item in paths)
    assert all(item["label"] == "Suggested Skill Path" for item in paths)
    assert all(item.get("distance", 0) <= 2 for item in paths)
    rec_match = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(rec_token),
    )
    assert rec_match.status_code == 200, rec_match.text
    assert rec_match.json()["suggested_skill_paths"] == []
    assert rec_match.json()["potential"] is not None
    career = client.get(
        f"/api/v1/candidates/{cid}/career-paths",
        headers=_bearer(cand_token),
        params={"job_id": job_id},
    )
    assert career.status_code == 200, career.text
    payload = career.json()
    assert payload["label"] == "Suggested Skill Path"
    assert any(item["target_skill"] == "Kubernetes" for item in payload["items"])
    recruiter_denied = client.get(
        f"/api/v1/candidates/{cid}/career-paths",
        headers=_bearer(rec_token),
        params={"job_id": job_id},
    )
    assert recruiter_denied.status_code == 403
    other_token, _ = _candidate(client, "career-other@example.com")
    assert (
        client.get(
            f"/api/v1/candidates/{cid}/career-paths",
            headers=_bearer(other_token),
        ).status_code
        == 403
    )
    k8s = db_session.query(Skill).filter(Skill.slug == "kubernetes").one()
    runs_before = db_session.query(MatchRun).count()
    skills_before = db_session.query(CandidateSkill).count()
    counter = client.post(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/counterfactual",
        headers=_bearer(cand_token),
        json={"skill_id": str(k8s.id)},
    )
    assert counter.status_code == 200
    cf = counter.json()
    assert cf["persisted"] is False
    assert cf["simulated_current_match"] > cf["baseline_current_match"]
    assert cf["potential_before"] is not None
    assert cf["potential_after"] is None
    db_session.expire_all()
    assert db_session.query(MatchRun).count() == runs_before
    assert db_session.query(CandidateSkill).count() == skills_before


def test_complete_match_potential_not_applicable(
    client: TestClient, seeded_ontology
) -> None:
    cand_token, cand_user = _candidate(client, "complete-match@example.com")
    rec_token, _ = _recruiter(client, "complete-rec@example.com", "Complete Org")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={"skills": [_mention("Machine Learning"), _mention("Python")], "projects": []},
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "Python machine learning role requiring those skills today.",
        ["Machine Learning", "Python"],
        [],
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert body["required_skill_coverage"] == 1.0
    assert body["potential"] is None
    assert body["potential_status"] == "not_applicable"
    assert body["potential"] != 1.0


def test_deep_learning_parent_graph_path(client: TestClient, seeded_ontology) -> None:
    cand_token, cand_user = _candidate(client, "dl-path@example.com")
    rec_token, _ = _recruiter(client, "dl-path-rec@example.com", "DL Path Org")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={"skills": [_mention("Machine Learning")], "projects": []},
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "Deep learning specialist role requiring deep learning now.",
        ["Deep Learning"],
        [],
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert body["required_skill_coverage"] == 0
    assert body["partial_skills"][0]["evidence_type"] == "parent"
    assert body["matched_skills"] == []
    assert body["potential_status"] == "available"
    path = next(item for item in body["explanations"] if item["type"] == "potential_graph_path")
    assert path["missing_skill"] == "Deep Learning"
    assert path["distance"] == 1
    assert any(item["target_skill"] == "Deep Learning" for item in body["suggested_skill_paths"])


def test_computer_vision_project_evidence(
    client: TestClient, db_session: Session, seeded_ontology
) -> None:
    cand_token, cand_user = _candidate(client, "cv-project@example.com")
    rec_token, _ = _recruiter(client, "cv-project-rec@example.com", "CV Org")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={
            "skills": [_mention("Machine Learning")],
            "projects": [
                {
                    "name": "Object Detection System",
                    "description": "Object Detection using OpenCV",
                }
            ],
        },
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "Computer vision engineer role requiring computer vision skills today.",
        ["Computer Vision"],
        [],
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert body["required_skill_coverage"] == 0
    assert all(item["skill"] != "Computer Vision" for item in body["matched_skills"])
    project_trace = next(item for item in body["explanations"] if item["type"] == "potential_project")
    assert project_trace["missing_skill"] == "Computer Vision"
    assert project_trace["project"] == "Object Detection System"
    assert project_trace["evidence"] == "OpenCV"
    db_session.expire_all()
    run = (
        db_session.query(MatchRun)
        .filter(MatchRun.candidate_id == uuid.UUID(cid), MatchRun.job_id == uuid.UUID(job_id))
        .order_by(MatchRun.created_at.desc())
        .first()
    )
    assert run is not None
    assert run.potential is not None
    assert run.scoring_mode == "baseline"
    assert run.model_version is None
    snap = db_session.query(FeatureSnapshot).filter(FeatureSnapshot.match_run_id == run.id).one()
    assert snap.feature_schema_version == "feature-schema-v2"
    assert snap.features["potential_project_evidence"] is not None
    explanation = db_session.query(MatchExplanation).filter(MatchExplanation.match_run_id == run.id).one()
    assert any(item["type"] == "potential_project" for item in explanation.traces)


def test_experience_and_semantic_http(client: TestClient, seeded_ontology) -> None:
    cand_token, cand_user = _candidate(client, "exp-pot@example.com")
    rec_token, _ = _recruiter(client, "exp-pot-rec@example.com", "Exp Org")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={
            "skills": [_mention("Python")],
            "experience": [
                {
                    "job_title": "Platform engineer",
                    "employer": "Cloud Co",
                    "description": "Deployed Docker containers in cloud infrastructure.",
                }
            ],
            "projects": [],
        },
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "Kubernetes engineer role requiring kubernetes expertise now.",
        ["Kubernetes"],
        [],
    )
    without = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert without["semantic_similarity_available"] is False
    assert without["potential_components"]["semantic_evidence"] is None
    assert any(item["type"] == "potential_experience" for item in without["explanations"])
    client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers=_bearer(cand_token))
    client.post(f"/api/v1/jobs/{job_id}/embedding", headers=_bearer(rec_token))
    with_emb = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert with_emb["semantic_similarity_available"] is True
    assert "semantic_evidence" in with_emb["potential_components"]
    assert any(item["type"] == "potential_semantic" for item in with_emb["explanations"])


def test_preferred_cannot_outrank_unrelated_required(client: TestClient, seeded_ontology) -> None:
    cand_token, cand_user = _candidate(client, "html-docker@example.com")
    rec_token, _ = _recruiter(client, "html-docker-rec@example.com", "Web Org")
    cid = cand_user["candidate_id"]
    _upload_draft(client, cand_token, cid)
    client.put(
        f"/api/v1/candidates/{cid}/profile",
        headers=_bearer(cand_token),
        json={
            "skills": [_mention("HTML"), _mention("CSS"), _mention("React"), _mention("Docker")],
            "projects": [],
            "experience": [],
            "certifications": [],
        },
    )
    _confirm_profile(client, cand_token, cid)
    job_id = _job_with_skills(
        client,
        rec_token,
        "ML kubernetes role requiring machine learning python kubernetes now.",
        ["Machine Learning", "Python", "Kubernetes"],
        ["Docker"],
    )
    body = client.get(
        f"/api/v1/candidates/{cid}/jobs/{job_id}/match",
        headers=_bearer(cand_token),
    ).json()
    assert body["required_skill_coverage"] == 0
    assert body["preferred_skill_coverage"] == 1.0
    assert body["potential"] is not None
    assert body["potential"] < 0.55
    assert body["current_match"] < 0.4
