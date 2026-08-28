from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog, RefreshSession, User
from app.models.enums import UserRole, UserStatus
from app.modules.identity.cookies import REFRESH_COOKIE_NAME
from app.modules.identity.csrf import hash_csrf
from app.modules.identity.password import hash_password
from app.modules.identity.tokens import generate_csrf_token, generate_refresh_token, hash_token, utcnow
from tests.auth_helpers import (
    PASSWORD,
    assert_no_secrets,
    cookie_value,
    login_user,
    refresh_hashes,
    register_user,
    stored_password_is_hashed,
)
from tests.conftest import auth_headers
from tests.factories import future


def test_register_candidate(client: TestClient, db_session: Session) -> None:
    body = register_user(client, email="cand@example.com", role="candidate")
    assert body["email"] == "cand@example.com"
    assert body["role"] == "candidate"
    assert body["status"] == "active"
    assert "password_hash" not in body
    stored_password_is_hashed(db_session, "cand@example.com", PASSWORD)
    user = db_session.query(User).filter(User.email == "cand@example.com").one()
    assert user.candidate is not None


def test_register_recruiter_creates_organization(client: TestClient, db_session: Session) -> None:
    body = register_user(
        client,
        email="recruiter@example.com",
        role="recruiter",
        organization_name="Northwind Labs",
    )
    assert body["role"] == "recruiter"
    user = db_session.query(User).filter(User.email == "recruiter@example.com").one()
    assert user.memberships
    assert user.memberships[0].organization.name == "Northwind Labs"
    assert user.candidate is None


def test_register_duplicate_email_conflict(client: TestClient) -> None:
    register_user(client, email="dup@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": PASSWORD, "role": "candidate"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_register_normalizes_email(client: TestClient, db_session: Session) -> None:
    body = register_user(client, email="  Ada.Lovelace@Example.COM ")
    assert body["email"] == "ada.lovelace@example.com"
    assert db_session.query(User).filter(User.email == "ada.lovelace@example.com").one()
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "ADA.LOVELACE@example.com", "password": PASSWORD, "role": "candidate"},
    )
    assert second.status_code == 409


def test_register_rejects_admin_self_registration(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "root@example.com", "password": PASSWORD, "role": "admin"},
    )
    assert response.status_code == 422
    assert "admin" in response.text.lower()
    assert db_session.query(User).filter(User.email == "root@example.com").first() is None


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "password123", "role": "candidate"},
    )
    assert response.status_code == 422


def test_login_success_sets_http_only_refresh_cookie(client: TestClient, db_session: Session) -> None:
    register_user(client, email="login@example.com")
    body = login_user(client, email="login@example.com")
    assert_no_secrets(body)
    assert "refresh_token" not in body
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert cookie_value(client) is not None
    hashes = refresh_hashes(db_session)
    assert hashes
    assert cookie_value(client) not in hashes
    assert all(len(item) == 64 for item in hashes)


def test_login_wrong_password_is_generic(client: TestClient) -> None:
    register_user(client, email="wrong@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "not-the-password"},
        headers=auth_headers(),
    )
    assert response.status_code == 401
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "not-the-password"},
        headers=auth_headers(),
    )
    assert missing.status_code == 401
    assert response.json()["detail"] == missing.json()["detail"]


def test_login_invalid_email_generic(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": PASSWORD},
        headers=auth_headers(),
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_suspended_user(client: TestClient, db_session: Session) -> None:
    register_user(client, email="paused@example.com")
    user = db_session.query(User).filter(User.email == "paused@example.com").one()
    user.status = UserStatus.SUSPENDED.value
    db_session.flush()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "paused@example.com", "password": PASSWORD},
        headers=auth_headers(),
    )
    assert response.status_code == 403
    assert "access_token" not in response.json()


def test_me_returns_safe_user(client: TestClient) -> None:
    register_user(client, email="me@example.com")
    tokens = login_user(client, email="me@example.com")
    response = client.get("/api/v1/auth/me", headers=bearer_only(tokens["_access"]))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert_no_secrets(body)


def bearer_only(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_refresh_rotates_token(client: TestClient, db_session: Session) -> None:
    register_user(client, email="refresh@example.com")
    first = login_user(client, email="refresh@example.com")
    old_raw = cookie_value(client)
    assert old_raw
    rotated = client.post(
        "/api/v1/auth/refresh",
        headers=auth_headers(csrf_token=first["_csrf"]),
    )
    assert rotated.status_code == 200, rotated.text
    new_raw = cookie_value(client)
    assert new_raw
    assert new_raw != old_raw
    assert old_raw not in refresh_hashes(db_session)
    assert hash_token(old_raw) in refresh_hashes(db_session)
    revoked = db_session.query(RefreshSession).filter(RefreshSession.token_hash == hash_token(old_raw)).one()
    assert revoked.revoked_at is not None

    reuse = client.post(
        "/api/v1/auth/refresh",
        headers={
            **auth_headers(csrf_token=first["_csrf"]),
            "Cookie": f"{REFRESH_COOKIE_NAME}={old_raw}",
        },
    )
    # Overwrite cookie for this request: TestClient may still send the new cookie.
    # Use a dedicated client cookie jar by setting the old token explicitly.
    client.cookies.set(REFRESH_COOKIE_NAME, old_raw, path="/api/v1/auth")
    reuse = client.post(
        "/api/v1/auth/refresh",
        headers=auth_headers(csrf_token=first["_csrf"]),
    )
    assert reuse.status_code == 401


def test_expired_refresh_rejected(client: TestClient, db_session: Session) -> None:
    register_user(client, email="expired@example.com")
    user = db_session.query(User).filter(User.email == "expired@example.com").one()
    raw = generate_refresh_token()
    csrf = generate_csrf_token()
    db_session.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=future(hours=-1),
            session_metadata={"family_id": str(uuid.uuid4()), "csrf_hash": hash_csrf(csrf)},
        )
    )
    db_session.flush()
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/refresh",
        headers={
            **auth_headers(csrf_token=csrf),
            "Cookie": f"{REFRESH_COOKIE_NAME}={raw}",
        },
    )
    assert response.status_code == 401


def test_revoked_refresh_rejected(client: TestClient, db_session: Session) -> None:
    register_user(client, email="revoked@example.com")
    tokens = login_user(client, email="revoked@example.com")
    row = db_session.query(RefreshSession).one()
    row.revoked_at = utcnow()
    db_session.flush()
    response = client.post("/api/v1/auth/refresh", headers=auth_headers(csrf_token=tokens["_csrf"]))
    assert response.status_code == 401


def test_logout_revokes_current_session_and_clears_cookie(client: TestClient, db_session: Session) -> None:
    register_user(client, email="out@example.com")
    tokens = login_user(client, email="out@example.com")
    response = client.post("/api/v1/auth/logout", headers=auth_headers(csrf_token=tokens["_csrf"]))
    assert response.status_code == 200
    row = db_session.query(RefreshSession).one()
    assert row.revoked_at is not None
    refresh = client.post("/api/v1/auth/refresh", headers=auth_headers(csrf_token=tokens["_csrf"]))
    assert refresh.status_code == 401


def test_logout_all_revokes_every_session(client: TestClient, db_session: Session) -> None:
    register_user(client, email="all@example.com")
    first = login_user(client, email="all@example.com")
    client.cookies.clear()
    second = login_user(client, email="all@example.com")
    assert db_session.query(RefreshSession).filter(RefreshSession.revoked_at.is_(None)).count() == 2
    response = client.post(
        "/api/v1/auth/logout-all",
        headers=bearer_only(second["_access"]),
    )
    assert response.status_code == 200
    assert db_session.query(RefreshSession).filter(RefreshSession.revoked_at.is_(None)).count() == 0
    client.cookies.set(REFRESH_COOKIE_NAME, cookie_value(client) or "", path="/api/v1/auth")
    assert first["_access"]


def test_audit_logs_omit_secrets(client: TestClient, db_session: Session) -> None:
    register_user(client, email="audit@example.com")
    login_user(client, email="audit@example.com")
    client.post(
        "/api/v1/auth/login",
        json={"email": "audit@example.com", "password": "nope-nope-nope"},
        headers=auth_headers(),
    )
    logs = db_session.query(AuditLog).all()
    assert {row.action for row in logs} >= {"auth.register", "auth.login_success", "auth.login_failure"}
    for row in logs:
        assert_no_secrets(row.audit_metadata)
        dumped = str(row.audit_metadata).lower()
        assert "password" not in dumped
        assert PASSWORD.lower() not in dumped
        assert "refresh" not in dumped


def test_refresh_requires_csrf_when_origin_is_absent(client: TestClient) -> None:
    register_user(client, email="csrf@example.com")
    login_user(client, email="csrf@example.com")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 403


def test_refresh_rejects_untrusted_origin(client: TestClient) -> None:
    register_user(client, email="origin@example.com")
    tokens = login_user(client, email="origin@example.com")
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://evil.example", "X-CSRF-Token": tokens["_csrf"]},
    )
    assert response.status_code == 403


def test_create_admin_only_via_persistence(client: TestClient, db_session: Session) -> None:
    user = User(
        email="admin@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    db_session.flush()
    tokens = login_user(client, email="admin@example.com")
    me = client.get("/api/v1/auth/me", headers=bearer_only(tokens["_access"]))
    assert me.json()["role"] == "admin"
