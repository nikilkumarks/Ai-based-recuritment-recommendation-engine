"""Allow shared content-addressed resume blobs.

Revision ID: 0003_resume_storage_key_shared
Revises: 0002_core_domain_schema
Create Date: 2026-08-27

Separate resume rows (authorization boundaries) may share one SHA-256 blob.
Drop uniqueness on storage_key if the previous create_all still had it.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect, text

revision: str = "0003_resume_storage_key_shared"
down_revision: str | None = "0002_core_domain_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    uniques = {item["name"] for item in inspector.get_unique_constraints("resumes")}
    if "uq_resumes_storage_key" in uniques:
        op.drop_constraint("uq_resumes_storage_key", "resumes", type_="unique")
    for idx in inspector.get_indexes("resumes"):
        cols = list(idx.get("column_names") or [])
        if cols == ["storage_key"] and idx.get("unique"):
            op.drop_index(idx["name"], table_name="resumes")
    inspector = inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("resumes")}
    if "ix_resumes_storage_key" not in indexes:
        op.create_index("ix_resumes_storage_key", "resumes", ["storage_key"])


def downgrade() -> None:
    bind = op.get_bind()
    dupes = bind.execute(
        text("SELECT storage_key FROM resumes GROUP BY storage_key HAVING COUNT(*) > 1")
    ).fetchall()
    if dupes:
        raise RuntimeError("Cannot restore unique storage_key while duplicate blob keys exist.")
    inspector = inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("resumes")}
    if "ix_resumes_storage_key" in indexes:
        op.drop_index("ix_resumes_storage_key", table_name="resumes")
    op.create_unique_constraint("uq_resumes_storage_key", "resumes", ["storage_key"])
