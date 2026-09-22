"""Widen match_runs.model_version for fixture and dated XGBoost versions.

Revision ID: 0009_match_run_model_version
Revises: 0008_ml_model_rejected
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_match_run_model_version"
down_revision: str | None = "0008_ml_model_rejected"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE match_runs ALTER COLUMN model_version TYPE VARCHAR(128)")


def downgrade() -> None:
    op.execute("ALTER TABLE match_runs ALTER COLUMN model_version TYPE VARCHAR(64)")
