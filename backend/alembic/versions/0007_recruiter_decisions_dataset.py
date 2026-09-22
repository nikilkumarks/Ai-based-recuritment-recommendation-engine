"""Phase 9 recruiter-decision and dataset snapshot columns.

Revision ID: 0007_recruiter_decisions_dataset
Revises: 0006_embedding_text_version
Create Date: 2026-08-28

Does not train models. Adds append-only decision lineage and dataset payload columns.
Idempotent: 0002 create_all may already have these columns when run against current models.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "0007_recruiter_decisions_dataset"
down_revision: str | None = "0006_embedding_text_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIONS_SQL = (
    "action IN ('view', 'compare', 'shortlist', 'reject', 'review', 'hire')"
)
LEGACY_ACTIONS_SQL = "action IN ('view', 'compare', 'shortlist', 'reject', 'hire')"


def _columns(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table)}


def _indexes(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_indexes(table) if item.get("name")}


def _fk_covers(inspector, table: str, column: str) -> bool:
    for item in inspector.get_foreign_keys(table):
        if list(item.get("constrained_columns") or []) == [column]:
            return True
    return False


def _drop_action_checks() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for item in inspector.get_check_constraints("recruiter_decisions"):
        name = item.get("name")
        sqltext = str(item.get("sqltext") or "").lower()
        if name and ("action" in str(name).lower() or "action" in sqltext):
            op.execute(f'ALTER TABLE recruiter_decisions DROP CONSTRAINT IF EXISTS "{name}"')
    op.execute("ALTER TABLE recruiter_decisions DROP CONSTRAINT IF EXISTS action")
    op.execute(
        "ALTER TABLE recruiter_decisions DROP CONSTRAINT IF EXISTS ck_recruiter_decisions_action"
    )


def _add_action_check(sql: str) -> None:
    _drop_action_checks()
    op.execute(f"ALTER TABLE recruiter_decisions ADD CONSTRAINT action CHECK ({sql})")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    uuid_type = postgresql.UUID(as_uuid=True)
    if "organization_id" not in columns:
        op.add_column(
            "recruiter_decisions",
            sa.Column("organization_id", uuid_type, nullable=True),
        )
    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    if "reason" not in columns:
        op.add_column("recruiter_decisions", sa.Column("reason", sa.String(length=64), nullable=True))
    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    if "note" not in columns:
        op.add_column("recruiter_decisions", sa.Column("note", sa.Text(), nullable=True))
    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    if "match_run_id" not in columns:
        op.add_column("recruiter_decisions", sa.Column("match_run_id", uuid_type, nullable=True))
    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    if "feature_snapshot_id" not in columns:
        op.add_column(
            "recruiter_decisions",
            sa.Column("feature_snapshot_id", uuid_type, nullable=True),
        )

    _add_action_check(ACTIONS_SQL)

    inspector = inspect(bind)
    if not _fk_covers(inspector, "recruiter_decisions", "organization_id"):
        op.create_foreign_key(
            "fk_recruiter_decisions_organization_id",
            "recruiter_decisions",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    inspector = inspect(bind)
    if not _fk_covers(inspector, "recruiter_decisions", "match_run_id"):
        op.create_foreign_key(
            "fk_recruiter_decisions_match_run_id",
            "recruiter_decisions",
            "match_runs",
            ["match_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
    inspector = inspect(bind)
    if not _fk_covers(inspector, "recruiter_decisions", "feature_snapshot_id"):
        op.create_foreign_key(
            "fk_recruiter_decisions_feature_snapshot_id",
            "recruiter_decisions",
            "feature_snapshots",
            ["feature_snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )

    inspector = inspect(bind)
    indexes = _indexes(inspector, "recruiter_decisions")
    if "ix_recruiter_decisions_organization_id" not in indexes:
        op.create_index(
            "ix_recruiter_decisions_organization_id",
            "recruiter_decisions",
            ["organization_id"],
        )
    inspector = inspect(bind)
    indexes = _indexes(inspector, "recruiter_decisions")
    if "ix_recruiter_decisions_candidate_job_created" not in indexes:
        op.create_index(
            "ix_recruiter_decisions_candidate_job_created",
            "recruiter_decisions",
            ["candidate_id", "job_id", "created_at"],
        )

    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    if "label_policy_version" not in ds_columns:
        op.add_column(
            "dataset_snapshots",
            sa.Column("label_policy_version", sa.String(length=64), nullable=True),
        )
    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    if "manifest" not in ds_columns:
        op.add_column(
            "dataset_snapshots",
            sa.Column("manifest", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        )
    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    if "rows" not in ds_columns:
        op.add_column(
            "dataset_snapshots",
            sa.Column("rows", jsonb, nullable=False, server_default=sa.text("'[]'::jsonb")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    if "rows" in ds_columns:
        op.drop_column("dataset_snapshots", "rows")
    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    if "manifest" in ds_columns:
        op.drop_column("dataset_snapshots", "manifest")
    inspector = inspect(bind)
    ds_columns = _columns(inspector, "dataset_snapshots")
    if "label_policy_version" in ds_columns:
        op.drop_column("dataset_snapshots", "label_policy_version")

    inspector = inspect(bind)
    indexes = _indexes(inspector, "recruiter_decisions")
    if "ix_recruiter_decisions_candidate_job_created" in indexes:
        op.drop_index("ix_recruiter_decisions_candidate_job_created", table_name="recruiter_decisions")
    inspector = inspect(bind)
    indexes = _indexes(inspector, "recruiter_decisions")
    if "ix_recruiter_decisions_organization_id" in indexes:
        op.drop_index("ix_recruiter_decisions_organization_id", table_name="recruiter_decisions")

    inspector = inspect(bind)
    for item in inspector.get_foreign_keys("recruiter_decisions"):
        cols = list(item.get("constrained_columns") or [])
        name = item.get("name")
        if name and cols and cols[0] in {"feature_snapshot_id", "match_run_id", "organization_id"}:
            op.execute(f'ALTER TABLE recruiter_decisions DROP CONSTRAINT IF EXISTS "{name}"')

    bind.execute(text("DELETE FROM recruiter_decisions WHERE action = 'review'"))
    _add_action_check(LEGACY_ACTIONS_SQL)

    inspector = inspect(bind)
    columns = _columns(inspector, "recruiter_decisions")
    for column in ("feature_snapshot_id", "match_run_id", "note", "reason", "organization_id"):
        inspector = inspect(bind)
        columns = _columns(inspector, "recruiter_decisions")
        if column in columns:
            op.drop_column("recruiter_decisions", column)
