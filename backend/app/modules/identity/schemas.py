"""DTOs for identity and authentication. Not SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import UserRole
from app.modules.identity.cookies import normalize_email
from app.modules.identity.password import validate_password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: str
    organization_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("role")
    @classmethod
    def role_must_be_self_serve(cls, value: str) -> str:
        lowered = value.strip().lower()
        if lowered == UserRole.ADMIN.value:
            raise ValueError("Admin accounts cannot be self-registered.")
        if lowered not in {UserRole.CANDIDATE.value, UserRole.RECRUITER.value}:
            raise ValueError("Role must be candidate or recruiter.")
        return lowered

    @field_validator("organization_name")
    @classmethod
    def strip_org_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def check_password_and_org(self) -> RegisterRequest:
        validate_password(self.password, self.email)
        if self.role == UserRole.RECRUITER.value and not self.organization_name:
            raise ValueError("Recruiters must provide an organization_name.")
        if self.role == UserRole.CANDIDATE.value and self.organization_name:
            raise ValueError("Candidates cannot create an organization during registration.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    status: str
    candidate_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None


def user_to_public(user) -> UserPublic:
    candidate_id = None
    candidate = getattr(user, "candidate", None)
    if candidate is not None:
        candidate_id = candidate.id
    organization_id = None
    memberships = getattr(user, "memberships", None) or []
    if memberships:
        organization_id = memberships[0].organization_id
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        candidate_id=candidate_id,
        organization_id=organization_id,
    )


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str
    user: UserPublic


class MessageResponse(BaseModel):
    message: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str


class AuthzProbeResponse(BaseModel):
    ok: bool = True
    resource_type: str
    resource_id: uuid.UUID | None = None
    role: str


class SessionView(BaseModel):
    """Internal test/debug shape — never returned by routers."""

    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: datetime
    revoked_at: datetime | None
