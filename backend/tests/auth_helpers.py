from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import RefreshSession, User
from app.modules.identity.cookies import REFRESH_COOKIE_NAME
from app.modules.identity.password import verify_password
from tests.conftest import auth_headers

PASSWORD = "correct-horse-battery"
SENSITIVE_JSON_KEYS = {
    "password",
    "password_hash",
    "refresh_token",
    "token_hash",
    "csrf_hash",
}


def register_user(
    client: TestClient,
    *,
    email: str,
    role: str = "candidate",
    password: str = PASSWORD,
    organization_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"email": email, "password": password, "role": role}
    if organization_name is not None:
        payload["organization_name"] = organization_name
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def login_user(
    client: TestClient,
    *,
    email: str,
    password: str = PASSWORD,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    body["_csrf"] = body["csrf_token"]
    body["_access"] = body["access_token"]
    return body


def bearer(access_token: str, csrf_token: str | None = None) -> dict[str, str]:
    return auth_headers(csrf_token=csrf_token, access_token=access_token)


def assert_no_secrets(payload: Any) -> None:
    if isinstance(payload, dict):
        lowered = {str(key).lower() for key in payload}
        assert lowered.isdisjoint(SENSITIVE_JSON_KEYS)
        for value in payload.values():
            assert_no_secrets(value)
    elif isinstance(payload, list):
        for item in payload:
            assert_no_secrets(item)


def stored_password_is_hashed(db_session: Session, email: str, plain: str) -> None:
    user = db_session.query(User).filter(User.email == email.lower()).one()
    assert user.password_hash != plain
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(plain, user.password_hash)


def refresh_hashes(db_session: Session) -> list[str]:
    return [row.token_hash for row in db_session.query(RefreshSession).all()]


def cookie_value(client: TestClient, name: str = REFRESH_COOKIE_NAME) -> str | None:
    return client.cookies.get(name)
