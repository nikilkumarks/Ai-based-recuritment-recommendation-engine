"""Add graph_snapshot JSONB for immutable ontology versions.

Revision ID: 0005_ontology_graph_snapshot
Revises: 0004_nlp_extracted_payload
Create Date: 2026-08-27

Stores a frozen catalog used by skill normalization. Does not modify 0001–0004.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0005_ontology_graph_snapshot"
down_revision: str | None = "0004_nlp_extracted_payload"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, "ontology_versions", "graph_snapshot"):
        op.add_column(
            "ontology_versions",
            sa.Column("graph_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "ontology_versions", "graph_snapshot"):
        op.drop_column("ontology_versions", "graph_snapshot")
