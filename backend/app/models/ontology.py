from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AliasSource,
    OntologyVersionStatus,
    SkillRelationType,
    SkillStatus,
    enum_values,
)


class Skill(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (CheckConstraint(f"status IN {enum_values(SkillStatus)}", name="status"),)

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SkillStatus.ACTIVE.value)

    aliases: Mapped[list[SkillAlias]] = relationship(back_populates="skill")


class SkillAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Alias strings are not skills. They resolve to a canonical skill_id."""

    __tablename__ = "skill_aliases"
    __table_args__ = (CheckConstraint(f"source IN {enum_values(AliasSource)}", name="source"),)

    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default=AliasSource.CURATED.value)

    skill: Mapped[Skill] = relationship(back_populates="aliases")


class SkillRelation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Graph edges only. Matching policy (parent ≠ child mastery) is applied later in code."""

    __tablename__ = "skill_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_skill_id",
            "target_skill_id",
            "relation",
            name="uq_skill_relations_edge",
        ),
        CheckConstraint("source_skill_id <> target_skill_id", name="no_self_relation"),
        CheckConstraint(f"relation IN {enum_values(SkillRelationType)}", name="relation"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="weight"),
    )

    source_skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1)

    source_skill: Mapped[Skill] = relationship(foreign_keys=[source_skill_id])
    target_skill: Mapped[Skill] = relationship(foreign_keys=[target_skill_id])


class OntologyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ontology_versions"
    __table_args__ = (
        CheckConstraint(f"status IN {enum_values(OntologyVersionStatus)}", name="status"),
        Index(
            "uq_ontology_versions_one_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OntologyVersionStatus.DRAFT.value
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graph_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
