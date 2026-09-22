"""Phase 10 model registry: rejected status and training_run linkage.

Revision ID: 0008_ml_model_rejected
Revises: 0007_recruiter_decisions_dataset
Create Date: 2026-08-28

Does not train models. Idempotent CHECK updates use raw SQL because the
naming convention prefixes constraint names (do not use op.drop_constraint).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0008_ml_model_rejected"
down_revision: str | None = "0007_recruiter_decisions_dataset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_SQL = "status IN ('candidate', 'active', 'rejected', 'retired')"
LEGACY_STATUS_SQL = "status IN ('candidate', 'active', 'retired')"


def _columns(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table)}


def _drop_status_checks() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for item in inspector.get_check_constraints("ml_models"):
        name = item.get("name")
        sqltext = str(item.get("sqltext") or "").lower()
        if name and ("status" in str(name).lower() or "status" in sqltext):
            op.execute(f'ALTER TABLE ml_models DROP CONSTRAINT IF EXISTS "{name}"')
    op.execute("ALTER TABLE ml_models DROP CONSTRAINT IF EXISTS status")
    op.execute("ALTER TABLE ml_models DROP CONSTRAINT IF EXISTS ck_ml_models_status")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = _columns(inspector, "ml_models")
    uuid_type = postgresql.UUID(as_uuid=True)
    if "training_run_id" not in columns:
        op.add_column("ml_models", sa.Column("training_run_id", uuid_type, nullable=True))
        op.create_foreign_key(
            "fk_ml_models_training_run_id_ml_training_runs",
            "ml_models",
            "ml_training_runs",
            ["training_run_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.execute("ALTER TABLE ml_models ALTER COLUMN version TYPE VARCHAR(128)")
    _drop_status_checks()
    op.execute(f"ALTER TABLE ml_models ADD CONSTRAINT status CHECK ({STATUS_SQL})")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = _columns(inspector, "ml_models")
    _drop_status_checks()
    op.execute(f"ALTER TABLE ml_models ADD CONSTRAINT status CHECK ({LEGACY_STATUS_SQL})")
    if "training_run_id" in columns:
        op.drop_constraint(
            "fk_ml_models_training_run_id_ml_training_runs", "ml_models", type_="foreignkey"
        )
        op.drop_column("ml_models", "training_run_id")
    op.execute("ALTER TABLE ml_models ALTER COLUMN version TYPE VARCHAR(64)")
