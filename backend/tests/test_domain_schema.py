from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Application,
    CandidateProfile,
    CandidateSkill,
    ExtractionRevision,
    FeatureSnapshot,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    MatchExplanation,
    MatchRun,
    MlModel,
    OrganizationMember,
    RecruiterDecision,
    RefreshSession,
    Resume,
    SkillAlias,
    SkillRelation,
)
from app.models.enums import (
    AliasSource,
    ApplicationStatus,
    ConfirmationStatus,
    MembershipRole,
    MlModelStatus,
    ParseStatus,
    RecruiterDecisionAction,
    ScoringMode,
    SkillAttributionSource,
    SkillRelationType,
    UserRole,
)
from tests.factories import (
    TEST_PASSWORD_HASH,
    future,
    make_candidate,
    make_job,
    make_org,
    make_profile,
    make_skill,
    make_user,
    token_hash,
)


def test_user_email_uniqueness(db_session: Session) -> None:
    db_session.add(make_user("ada@example.com"))
    db_session.flush()
    db_session.add(make_user("ada@example.com", role=UserRole.RECRUITER.value))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_email_must_be_normalized(db_session: Session) -> None:
    user = make_user("ada@example.com")
    user.email = "Ada@Example.com"
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_organization_membership_uniqueness(db_session: Session) -> None:
    org = make_org()
    user = make_user("recruiter@example.com", role=UserRole.RECRUITER.value)
    db_session.add_all([org, user])
    db_session.flush()
    db_session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            membership_role=MembershipRole.RECRUITER.value,
        )
    )
    db_session.flush()
    db_session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            membership_role=MembershipRole.OWNER.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_candidate_belongs_to_exactly_one_user(db_session: Session) -> None:
    user = make_user("cand@example.com")
    db_session.add(user)
    db_session.flush()
    db_session.add(make_candidate(user))
    db_session.flush()
    db_session.add(make_candidate(user))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_skill_alias_uniqueness(db_session: Session) -> None:
    skill = make_skill("Machine Learning")
    db_session.add(skill)
    db_session.flush()
    db_session.add(
        SkillAlias(
            skill_id=skill.id,
            alias="ML",
            normalized_alias="ml",
            source=AliasSource.CURATED.value,
        )
    )
    db_session.flush()
    other = make_skill("Meta Learning", slug="meta-learning")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        SkillAlias(
            skill_id=other.id,
            alias="ml",
            normalized_alias="ml",
            source=AliasSource.CURATED.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_skill_relation_rejects_self_and_duplicates(db_session: Session) -> None:
    parent = make_skill("Artificial Intelligence", slug="artificial-intelligence")
    child = make_skill("Machine Learning")
    db_session.add_all([parent, child])
    db_session.flush()
    db_session.add(
        SkillRelation(
            source_skill_id=parent.id,
            target_skill_id=parent.id,
            relation=SkillRelationType.PARENT_OF.value,
            weight=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
    parent = make_skill("Artificial Intelligence", slug="artificial-intelligence")
    child = make_skill("Machine Learning")
    db_session.add_all([parent, child])
    db_session.flush()
    db_session.add(
        SkillRelation(
            source_skill_id=parent.id,
            target_skill_id=child.id,
            relation=SkillRelationType.PARENT_OF.value,
            weight=1,
        )
    )
    db_session.flush()
    db_session.add(
        SkillRelation(
            source_skill_id=parent.id,
            target_skill_id=child.id,
            relation=SkillRelationType.PARENT_OF.value,
            weight=0.5,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_candidate_skill_links_canonical_skill(db_session: Session) -> None:
    user = make_user("skills@example.com")
    candidate = make_candidate(user)
    profile = make_profile(candidate)
    skill = make_skill("Deep Learning")
    db_session.add_all([user, candidate, profile, skill])
    db_session.flush()
    first = CandidateSkill(
        candidate_profile_id=profile.id,
        skill_id=skill.id,
        source=SkillAttributionSource.CANDIDATE.value,
        confidence=1,
    )
    db_session.add(first)
    db_session.flush()
    assert first.skill_id == skill.id
    db_session.add(
        CandidateSkill(
            candidate_profile_id=profile.id,
            skill_id=skill.id,
            source=SkillAttributionSource.EXTRACTION.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_job_required_and_preferred_skills(db_session: Session) -> None:
    org = make_org()
    recruiter = make_user("jobs@example.com", role=UserRole.RECRUITER.value)
    db_session.add_all([org, recruiter])
    db_session.flush()
    job = make_job(org, recruiter)
    req = JobRequirement(job=job, confirmation_status=ConfirmationStatus.CONFIRMED.value)
    ml = make_skill("Machine Learning")
    nlp = make_skill("Natural Language Processing", slug="nlp")
    db_session.add_all([job, req, ml, nlp])
    db_session.flush()
    db_session.add_all(
        [
            JobRequiredSkill(job_requirement_id=req.id, skill_id=ml.id, importance="critical"),
            JobPreferredSkill(job_requirement_id=req.id, skill_id=nlp.id, importance="normal"),
        ]
    )
    db_session.flush()
    db_session.add(JobRequiredSkill(job_requirement_id=req.id, skill_id=ml.id, importance="high"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_match_run_persistence_without_fake_scores(db_session: Session) -> None:
    org = make_org()
    recruiter = make_user("ranker@example.com", role=UserRole.RECRUITER.value)
    user = make_user("target@example.com")
    candidate = make_candidate(user)
    db_session.add_all([org, recruiter, user, candidate])
    db_session.flush()
    job = make_job(org, recruiter)
    db_session.add(job)
    db_session.flush()
    run = MatchRun(
        candidate_id=candidate.id,
        job_id=job.id,
        scoring_mode=ScoringMode.BASELINE.value,
        model_version=None,
        current_match=None,
        potential=None,
        unconfirmed_profile=False,
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(MatchExplanation(match_run_id=run.id, traces=[]))
    db_session.add(
        FeatureSnapshot(
            match_run_id=run.id,
            feature_schema_version="feature_schema_v1",
            features={"req_skill_exact_coverage": 0},
        )
    )
    db_session.flush()
    stored = db_session.get(MatchRun, run.id)
    assert stored is not None
    assert stored.scoring_mode == ScoringMode.BASELINE.value
    assert stored.current_match is None
    assert stored.model_version is None


def test_trained_match_run_requires_model_version(db_session: Session) -> None:
    org = make_org()
    recruiter = make_user("ml@example.com", role=UserRole.RECRUITER.value)
    user = make_user("c@example.com")
    candidate = make_candidate(user)
    db_session.add_all([org, recruiter, user, candidate])
    db_session.flush()
    job = make_job(org, recruiter)
    db_session.add(job)
    db_session.flush()
    db_session.add(
        MatchRun(
            candidate_id=candidate.id,
            job_id=job.id,
            scoring_mode=ScoringMode.TRAINED.value,
            model_version=None,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_model_registry_single_active(db_session: Session) -> None:
    db_session.add(
        MlModel(
            version="xgb-1",
            model_type="xgboost",
            artifact_uri="ml/artifacts/xgb-1/model.json",
            feature_schema_version="feature_schema_v1",
            status=MlModelStatus.ACTIVE.value,
        )
    )
    db_session.flush()
    db_session.add(
        MlModel(
            version="xgb-2",
            model_type="xgboost",
            artifact_uri="ml/artifacts/xgb-2/model.json",
            feature_schema_version="feature_schema_v1",
            status=MlModelStatus.ACTIVE.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_foreign_key_integrity(db_session: Session) -> None:
    missing = uuid.uuid4()
    db_session.add(
        OrganizationMember(
            organization_id=missing,
            user_id=missing,
            membership_role=MembershipRole.RECRUITER.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_application_uniqueness(db_session: Session) -> None:
    org = make_org()
    recruiter = make_user("apps@example.com", role=UserRole.RECRUITER.value)
    user = make_user("apply@example.com")
    candidate = make_candidate(user)
    db_session.add_all([org, recruiter, user, candidate])
    db_session.flush()
    job = make_job(org, recruiter)
    db_session.add(job)
    db_session.flush()
    db_session.add(
        Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=ApplicationStatus.APPLIED.value,
        )
    )
    db_session.flush()
    db_session.add(
        Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=ApplicationStatus.WITHDRAWN.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_recruiter_decision_persistence(db_session: Session) -> None:
    org = make_org()
    recruiter = make_user("decisions@example.com", role=UserRole.RECRUITER.value)
    user = make_user("seen@example.com")
    candidate = make_candidate(user)
    db_session.add_all([org, recruiter, user, candidate])
    db_session.flush()
    job = make_job(org, recruiter)
    db_session.add(job)
    db_session.flush()
    decision = RecruiterDecision(
        recruiter_id=recruiter.id,
        job_id=job.id,
        candidate_id=candidate.id,
        action=RecruiterDecisionAction.SHORTLIST.value,
        decision_metadata={"note": "schema-only test"},
    )
    db_session.add(decision)
    db_session.flush()
    stored = db_session.get(RecruiterDecision, decision.id)
    assert stored is not None
    assert stored.action == RecruiterDecisionAction.SHORTLIST.value
    assert stored.decision_metadata["note"] == "schema-only test"


def test_refresh_session_stores_hash_not_raw_token(db_session: Session) -> None:
    user = make_user("session@example.com")
    db_session.add(user)
    db_session.flush()
    raw = "this-must-not-be-persisted"
    db_session.add(RefreshSession(user_id=user.id, token_hash=token_hash(raw), expires_at=future()))
    db_session.flush()
    row = db_session.query(RefreshSession).one()
    assert raw not in row.token_hash
    assert row.token_hash == token_hash(raw)
    assert user.password_hash == TEST_PASSWORD_HASH


def test_deleting_resume_keeps_confirmed_profile(db_session: Session) -> None:
    user = make_user("resume@example.com")
    candidate = make_candidate(user)
    db_session.add_all([user, candidate])
    db_session.flush()
    resume = Resume(
        candidate_id=candidate.id,
        storage_key="sha256/" + "a" * 64,
        original_filename="cv.pdf",
        mime_type="application/pdf",
        file_size=1024,
        sha256="a" * 64,
        parse_status=ParseStatus.READY.value,
    )
    db_session.add(resume)
    db_session.flush()
    revision = ExtractionRevision(
        resume_id=resume.id,
        revision_number=1,
        parser_version="unspecified",
        extraction_payload={"skills": ["ML"]},
    )
    db_session.add(revision)
    db_session.flush()
    profile = CandidateProfile(
        candidate_id=candidate.id,
        source_revision_id=revision.id,
        profile_version=1,
        confirmation_status=ConfirmationStatus.CONFIRMED.value,
        summary="Kept after resume delete",
    )
    db_session.add(profile)
    db_session.flush()
    profile_id = profile.id
    resume_id = resume.id
    revision_id = revision.id
    db_session.execute(delete(Resume).where(Resume.id == resume_id))
    db_session.flush()
    db_session.expire_all()
    kept = db_session.get(CandidateProfile, profile_id)
    assert kept is not None
    assert kept.summary == "Kept after resume delete"
    assert kept.source_revision_id is None
    assert db_session.get(Resume, resume_id) is None
    assert db_session.get(ExtractionRevision, revision_id) is None


def test_pgvector_extension_enabled(db_session: Session) -> None:
    name = db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    ).scalar()
    assert name == "vector"
    tables = inspect(db_session.get_bind()).get_table_names()
    for table in ("users", "match_runs", "embeddings", "ml_models", "skill_aliases"):
        assert table in tables
