"""Core domain schema.

Revision ID: 0002_core_domain_schema
Revises: 0001_enable_pgvector
Create Date: 2026-08-27

Creates identity, candidate, ontology, job, matching, and ML registry tables.
Does not insert users, jobs, scores, or model artifacts.
"""

from collections.abc import Sequence

from alembic import op

import app.models  # noqa: F401
from app.models.base import Base

revision: str = "0002_core_domain_schema"
down_revision: str | None = "0001_enable_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
