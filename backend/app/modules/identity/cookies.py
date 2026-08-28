from __future__ import annotations

import re

from fastapi import Response

from app.core.config import get_settings

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def slugify_organization(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return (slug or "organization")[:96]


def _cookie_kwargs() -> dict[str, str | bool | None]:
    settings = get_settings()
    samesite = settings.cookie_samesite_value()
    return {
        "httponly": True,
        "secure": settings.cookie_secure_enabled(),
        "samesite": samesite,
        "path": REFRESH_COOKIE_PATH,
    }


def set_refresh_cookie(response: Response, raw_refresh_token: str, max_age_seconds: int) -> None:
    kwargs = _cookie_kwargs()
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        raw_refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=bool(kwargs["secure"]),
        samesite=str(kwargs["samesite"]),
        path=REFRESH_COOKIE_PATH,
    )


def set_csrf_cookie(response: Response, csrf_token: str, max_age_seconds: int) -> None:
    """Readable CSRF cookie for same-origin clients. Cross-origin SPAs use the JSON csrf_token."""
    settings = get_settings()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age_seconds,
        httponly=False,
        secure=settings.cookie_secure_enabled(),
        samesite=settings.cookie_samesite_value(),
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    samesite = settings.cookie_samesite_value()
    secure = settings.cookie_secure_enabled()
    for name in (REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME):
        response.delete_cookie(
            name,
            path=REFRESH_COOKIE_PATH,
            secure=secure,
            httponly=name == REFRESH_COOKIE_NAME,
            samesite=samesite,
        )
