"""HTTP routes for authentication. Thin: validate, call service, set cookies, return DTOs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.core.rate_limit import rate_limit
from app.models import User
from app.modules.identity.cookies import clear_auth_cookies, set_csrf_cookie, set_refresh_cookie
from app.modules.identity.csrf import require_trusted_origin
from app.modules.identity.dependencies import (
    get_current_active_user,
    get_identity_service,
    get_refresh_token_cookie,
    require_cookie_csrf,
)
from app.modules.identity.schemas import (
    AuthTokenResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserPublic,
    user_to_public,
)
from app.modules.identity.service import IdentityService, IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookies(response: Response, issued: IssuedSession) -> None:
    set_refresh_cookie(response, issued.refresh_token, issued.refresh_max_age)
    set_csrf_cookie(response, issued.csrf_token, issued.refresh_max_age)


def _token_payload(issued: IssuedSession) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in,
        csrf_token=issued.csrf_token,
        user=user_to_public(issued.user),
    )


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=201,
    dependencies=[Depends(rate_limit("register", "rate_limit_register_per_minute"))],
)
def register(
    payload: RegisterRequest,
    service: IdentityService = Depends(get_identity_service),
) -> UserPublic:
    user = service.register(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        organization_name=payload.organization_name,
    )
    return user_to_public(user)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    dependencies=[Depends(rate_limit("login", "rate_limit_login_per_minute"))],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: IdentityService = Depends(get_identity_service),
) -> AuthTokenResponse:
    require_trusted_origin(request)
    issued = service.login(email=payload.email, password=payload.password)
    _set_session_cookies(response, issued)
    return _token_payload(issued)


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    dependencies=[Depends(rate_limit("refresh", "rate_limit_refresh_per_minute"))],
)
def refresh(
    response: Response,
    service: IdentityService = Depends(get_identity_service),
    refresh_token: str | None = Depends(get_refresh_token_cookie),
    csrf_token: str | None = Depends(require_cookie_csrf),
) -> AuthTokenResponse:
    issued = service.refresh(raw_refresh_token=refresh_token, csrf_token=csrf_token)
    _set_session_cookies(response, issued)
    return _token_payload(issued)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    service: IdentityService = Depends(get_identity_service),
    refresh_token: str | None = Depends(get_refresh_token_cookie),
    csrf_token: str | None = Depends(require_cookie_csrf),
) -> MessageResponse:
    service.logout(raw_refresh_token=refresh_token, csrf_token=csrf_token)
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    user: User = Depends(get_current_active_user),
    service: IdentityService = Depends(get_identity_service),
) -> MessageResponse:
    service.logout_all(user=user)
    clear_auth_cookies(response)
    return MessageResponse(message="All sessions signed out.")


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_active_user)) -> UserPublic:
    return user_to_public(user)
