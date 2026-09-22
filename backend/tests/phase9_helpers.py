"""Shared Phase 9 test helpers. Do not invent recruiter labels."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Candidate, OrganizationMember, User
from app.models.enums import MembershipRole, UserRole, UserStatus
from app.modules.identity.password import hash_password
from tests.auth_helpers import PASSWORD, login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines

SCENARIO_JD = """
Machine learning engineer role.
Required skills: Machine Learning, Python, and Kubernetes.
Preferred: Docker.
Minimum 3 years of experience. Education: bachelor.
""".strip()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def mention(text: str) -> dict[str, str]:
    return {"raw_text": text, "normalized_text": text.lower(), "evidence": text}


def candidate_account(client: TestClient, email: str):
    register_user(client, email=email, role="candidate")
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def recruiter_account(client: TestClient, email: str, org: str):
    register_user(client, email=email, role="recruiter", organization_name=org)
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def admin_token(client: TestClient, db_session: Session, email: str) -> str:
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


def upload_draft(client: TestClient, token: str, candidate_id: str) -> None:
    lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
    uploaded = client.post(
        f"/api/v1/candidates/{candidate_id}/resumes",
        headers=bearer(token),
        files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text


def confirm_profile(client: TestClient, token: str, candidate_id: str) -> None:
    confirmed = client.post(
        f"/api/v1/candidates/{candidate_id}/profile/confirm",
        headers=bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text


def set_skills(client: TestClient, token: str, candidate_id: str, skills: list[str]) -> None:
    updated = client.put(
        f"/api/v1/candidates/{candidate_id}/profile",
        headers=bearer(token),
        json={"skills": [mention(name) for name in skills]},
    )
    assert updated.status_code == 200, updated.text
    confirm_profile(client, token, candidate_id)


def make_discoverable(db_session: Session, candidate_id: str) -> None:
    row = db_session.query(Candidate).filter(Candidate.id == uuid.UUID(candidate_id)).one()
    row.preferences = {"discoverable": True}
    db_session.flush()


def job_with_scenario_skills(client: TestClient, token: str) -> str:
    created = client.post(
        "/api/v1/jobs",
        headers=bearer(token),
        json={"title": "Engineer", "description_raw": SCENARIO_JD},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/jobs/{job_id}/requirements",
        headers=bearer(token),
        json={
            "required_skills": [
                mention("Machine Learning"),
                mention("Python"),
                mention("Kubernetes"),
            ],
            "preferred_skills": [mention("Docker")],
            "min_years_experience": 3,
            "education_level": "bachelor",
        },
    )
    assert updated.status_code == 200, updated.text
    confirmed = client.post(
        f"/api/v1/jobs/{job_id}/requirements/confirm",
        headers=bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text
    return job_id


def prepared_candidate(
    client: TestClient, db_session: Session, email: str, skills: list[str]
) -> tuple[str, dict]:
    token, user = candidate_account(client, email)
    cid = user["candidate_id"]
    upload_draft(client, token, cid)
    set_skills(client, token, cid, skills)
    make_discoverable(db_session, cid)
    return token, user


def add_org_recruiter(
    client: TestClient,
    db_session: Session,
    *,
    email: str,
    organization_id: uuid.UUID,
) -> str:
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        role=UserRole.RECRUITER.value,
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        OrganizationMember(
            organization_id=organization_id,
            user_id=user.id,
            membership_role=MembershipRole.RECRUITER.value,
        )
    )
    db_session.flush()
    return login_user(client, email=email)["_access"]
