from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Application, Candidate, User
from app.models.enums import ApplicationStatus, UserRole, UserStatus
from app.modules.identity.password import hash_password
from tests.auth_helpers import PASSWORD, login_user, register_user
from tests.factories import make_job, make_org


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str) -> str:
    return login_user(client, email=email)["_access"]


def test_candidate_cannot_access_recruiter_or_admin_probes(client: TestClient) -> None:
    register_user(client, email="cand-rbac@example.com", role="candidate")
    token = _login(client, "cand-rbac@example.com")
    assert client.get("/api/v1/authz/recruiter", headers=_bearer(token)).status_code == 403
    assert client.get("/api/v1/authz/admin", headers=_bearer(token)).status_code == 403
    assert client.get("/api/v1/authz/candidate", headers=_bearer(token)).status_code == 200


def test_recruiter_cannot_access_admin_probe(client: TestClient) -> None:
    register_user(
        client,
        email="rec-rbac@example.com",
        role="recruiter",
        organization_name="RBAC Corp",
    )
    token = _login(client, "rec-rbac@example.com")
    assert client.get("/api/v1/authz/admin", headers=_bearer(token)).status_code == 403
    assert client.get("/api/v1/authz/recruiter", headers=_bearer(token)).status_code == 200
    assert client.get("/api/v1/authz/candidate", headers=_bearer(token)).status_code == 403


def test_admin_can_access_admin_probe(client: TestClient, db_session: Session) -> None:
    db_session.add(
        User(
            email="admin-rbac@example.com",
            password_hash=hash_password(PASSWORD),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    db_session.flush()
    token = _login(client, "admin-rbac@example.com")
    assert client.get("/api/v1/authz/admin", headers=_bearer(token)).status_code == 200
    assert client.get("/api/v1/authz/candidate", headers=_bearer(token)).status_code == 403


def test_candidate_cannot_access_another_candidate(client: TestClient, db_session: Session) -> None:
    register_user(client, email="alice@example.com", role="candidate")
    register_user(client, email="bob@example.com", role="candidate")
    alice = db_session.query(User).filter(User.email == "alice@example.com").one()
    bob = db_session.query(User).filter(User.email == "bob@example.com").one()
    alice_cand = db_session.query(Candidate).filter(Candidate.user_id == alice.id).one()
    bob_cand = db_session.query(Candidate).filter(Candidate.user_id == bob.id).one()
    alice_token = _login(client, "alice@example.com")
    own = client.get(f"/api/v1/authz/candidates/{alice_cand.id}", headers=_bearer(alice_token))
    other = client.get(f"/api/v1/authz/candidates/{bob_cand.id}", headers=_bearer(alice_token))
    assert own.status_code == 200
    assert other.status_code == 403
    missing = client.get(f"/api/v1/authz/candidates/{uuid.uuid4()}", headers=_bearer(alice_token))
    assert missing.status_code == 404


def test_recruiter_org_isolation(client: TestClient, db_session: Session) -> None:
    register_user(client, email="org-a@example.com", role="recruiter", organization_name="Org Alpha")
    register_user(client, email="org-b@example.com", role="recruiter", organization_name="Org Beta")
    recruiter_a = db_session.query(User).filter(User.email == "org-a@example.com").one()
    recruiter_b = db_session.query(User).filter(User.email == "org-b@example.com").one()
    org_a = recruiter_a.memberships[0].organization
    org_b = recruiter_b.memberships[0].organization
    job_a = make_job(org_a, recruiter_a, title="Alpha Role")
    job_b = make_job(org_b, recruiter_b, title="Beta Role")
    db_session.add_all([job_a, job_b])
    db_session.flush()

    token_a = _login(client, "org-a@example.com")
    assert client.get(f"/api/v1/authz/organizations/{org_a.id}", headers=_bearer(token_a)).status_code == 200
    assert client.get(f"/api/v1/authz/organizations/{org_b.id}", headers=_bearer(token_a)).status_code == 403
    assert client.get(f"/api/v1/authz/jobs/{job_a.id}", headers=_bearer(token_a)).status_code == 200
    assert client.get(f"/api/v1/authz/jobs/{job_b.id}", headers=_bearer(token_a)).status_code == 403
    assert client.get(f"/api/v1/authz/jobs/{job_b.id}/decisions", headers=_bearer(token_a)).status_code == 403


def test_client_supplied_org_id_is_not_trusted(client: TestClient, db_session: Session) -> None:
    register_user(client, email="spoof@example.com", role="recruiter", organization_name="Spoof Co")
    other = make_org("Hidden Org", slug="hidden-org")
    db_session.add(other)
    db_session.flush()
    token = _login(client, "spoof@example.com")
    response = client.get(f"/api/v1/authz/organizations/{other.id}", headers=_bearer(token))
    assert response.status_code == 403


def test_recruiter_cannot_view_out_of_scope_candidate(client: TestClient, db_session: Session) -> None:
    register_user(client, email="scope-rec@example.com", role="recruiter", organization_name="Scope Org")
    register_user(client, email="scope-cand@example.com", role="candidate")
    recruiter = db_session.query(User).filter(User.email == "scope-rec@example.com").one()
    candidate_user = db_session.query(User).filter(User.email == "scope-cand@example.com").one()
    candidate = db_session.query(Candidate).filter(Candidate.user_id == candidate_user.id).one()
    token = _login(client, "scope-rec@example.com")
    denied = client.get(
        f"/api/v1/authz/candidates/{candidate.id}/recruiter-view",
        headers=_bearer(token),
    )
    assert denied.status_code == 403

    job = make_job(recruiter.memberships[0].organization, recruiter)
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
    allowed = client.get(
        f"/api/v1/authz/candidates/{candidate.id}/recruiter-view",
        headers=_bearer(token),
    )
    assert allowed.status_code == 200


def test_discoverable_candidate_is_in_default_scope(client: TestClient, db_session: Session) -> None:
    register_user(client, email="disc-rec@example.com", role="recruiter", organization_name="Discover Org")
    register_user(client, email="disc-cand@example.com", role="candidate")
    candidate_user = db_session.query(User).filter(User.email == "disc-cand@example.com").one()
    candidate = db_session.query(Candidate).filter(Candidate.user_id == candidate_user.id).one()
    candidate.preferences = {"discoverable": True}
    db_session.flush()
    token = _login(client, "disc-rec@example.com")
    allowed = client.get(
        f"/api/v1/authz/candidates/{candidate.id}/recruiter-view",
        headers=_bearer(token),
    )
    assert allowed.status_code == 200


def test_suspended_user_cannot_use_authenticated_endpoints(client: TestClient, db_session: Session) -> None:
    register_user(client, email="frozen@example.com")
    token = _login(client, "frozen@example.com")
    user = db_session.query(User).filter(User.email == "frozen@example.com").one()
    user.status = UserStatus.SUSPENDED.value
    db_session.flush()
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 403
