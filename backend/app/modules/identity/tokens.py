"""Access JWT and refresh-token helpers. Refresh tokens are stored hashed only."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.core.security import sha256_hex

REFRESH_TOKEN_BYTES = 32


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(raw: str) -> str:
    return sha256_hex(raw)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(
    *,
    user_id: uuid.UUID,
    role: str,
    jti: uuid.UUID | None = None,
) -> tuple[str, datetime]:
    settings = get_settings()
    now = utcnow()
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": str(jti or uuid.uuid4()),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise UnauthenticatedError("Invalid or expired access token.") from exc
    if payload.get("typ") != "access" or not payload.get("sub"):
        raise UnauthenticatedError("Invalid or expired access token.")
    return payload


def refresh_expiry() -> datetime:
    settings = get_settings()
    return utcnow() + timedelta(days=settings.refresh_token_expire_days)
