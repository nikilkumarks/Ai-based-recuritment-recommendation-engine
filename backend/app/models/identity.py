from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    MembershipRole,
    OrganizationStatus,
    UserRole,
    UserStatus,
    enum_values,
)

if TYPE_CHECKING:
    from app.models.candidates import Candidate
    from app.models.jobs import Job


class User(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN {enum_values(UserRole)}", name="role"),
        CheckConstraint(f"status IN {enum_values(UserStatus)}", name="status"),
        CheckConstraint("email = lower(email)", name="email_normalized"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=UserStatus.PENDING.value)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[OrganizationMember]] = relationship(back_populates="user")
    candidate: Mapped[Candidate | None] = relationship(back_populates="user")
    refresh_sessions: Mapped[list[RefreshSession]] = relationship(back_populates="user")


class Organization(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint(f"status IN {enum_values(OrganizationStatus)}", name="status"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OrganizationStatus.ACTIVE.value
    )

    members: Mapped[list[OrganizationMember]] = relationship(back_populates="organization")
    jobs: Mapped[list[Job]] = relationship(back_populates="organization")


class OrganizationMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
        CheckConstraint(f"membership_role IN {enum_values(MembershipRole)}", name="membership_role"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_role: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MembershipRole.RECRUITER.value
    )

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class RefreshSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Refresh-token persistence. Store only a hash, never the raw token."""

    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    user: Mapped[User] = relationship(back_populates="refresh_sessions")
