"""CSRF protection for cookie-authenticated state changes.

httpOnly cookies are not readable by JavaScript, but the browser still attaches them to
cross-site requests unless SameSite and Origin/CSRF checks block that. Refresh and logout
therefore require a matching CSRF token header in addition to the refresh cookie.

The access token is sent as `Authorization: Bearer` and is not stored in a cookie, so
Bearer-authenticated routes are not cookie-CSRF endpoints.
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.core.security import sha256_hex

CSRF_HEADER = "X-CSRF-Token"


def hash_csrf(raw: str) -> str:
    return sha256_hex(raw)


def csrf_tokens_match(presented: str, stored_hash: str) -> bool:
    if not presented or not stored_hash:
        return False
    return hash_csrf(presented) == stored_hash


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        # Non-browser clients (curl, TestClient without Origin). CSRF header still required.
        return
    allowed = get_settings().cors_origin_list()
    if origin not in allowed:
        raise ForbiddenError("Cross-origin request was blocked.")


def read_csrf_header(request: Request) -> str:
    return request.headers.get(CSRF_HEADER, "").strip()
