"""Reusable authentication dependencies. Authorization policies live in modules/authorization."""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthenticatedError
from app.models import User
from app.models.enums import UserStatus
from app.modules.identity.cookies import REFRESH_COOKIE_NAME
from app.modules.identity.csrf import read_csrf_header, require_trusted_origin
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import IdentityService
from app.modules.identity.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_identity_service(db: Session = Depends(get_db)) -> IdentityService:
    return IdentityService(db)


def get_refresh_token_cookie(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)


def require_cookie_csrf(request: Request) -> str | None:
    require_trusted_origin(request)
    token = read_csrf_header(request)
    origin = request.headers.get("origin")
    trusted_origin = bool(origin) and origin in get_settings().cors_origin_list()
    if token:
        return token
    if trusted_origin:
        return None
    raise ForbiddenError("CSRF token was missing or invalid.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError("Authentication required.")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise UnauthenticatedError("Invalid or expired access token.") from exc
    user = IdentityRepository(db).get_user_by_id(user_id)
    if user is None:
        raise UnauthenticatedError("Authentication required.")
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if user.status != UserStatus.ACTIVE.value:
        raise ForbiddenError("This account cannot use authenticated endpoints.")
    return user


def require_authenticated_user(user: User = Depends(get_current_active_user)) -> User:
    return user
