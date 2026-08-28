"""Add extracted_payload JSONB for NLP drafts.

Revision ID: 0004_nlp_extracted_payload
Revises: 0003_resume_storage_key_shared
Create Date: 2026-08-27

Stores raw NLP drafts on candidate_profiles and job_requirements.
Does not add canonical skill IDs. Does not modify 0001–0003.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0004_nlp_extracted_payload"
down_revision: str | None = "0003_resume_storage_key_shared"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_TYPES = (
    "resume_parse",
    "resume_nlp",
    "resume_embed",
    "profile_embed",
    "job_parse",
    "job_embed",
    "match_batch",
)


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    if not _has_column(inspector, "candidate_profiles", "extracted_payload"):
        op.add_column(
            "candidate_profiles",
            sa.Column(
                "extracted_payload",
                jsonb,
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
    inspector = inspect(bind)
    if not _has_column(inspector, "job_requirements", "extracted_payload"):
        op.add_column(
            "job_requirements",
            sa.Column(
                "extracted_payload",
                jsonb,
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS ck_processing_jobs_type")
    values = ", ".join(f"'{item}'" for item in JOB_TYPES)
    sql = f"ALTER TABLE processing_jobs ADD CONSTRAINT ck_processing_jobs_type CHECK (type IN ({values}))"
    op.execute(sql)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "job_requirements", "extracted_payload"):
        op.drop_column("job_requirements", "extracted_payload")
    inspector = inspect(bind)
    if _has_column(inspector, "candidate_profiles", "extracted_payload"):
        op.drop_column("candidate_profiles", "extracted_payload")
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS ck_processing_jobs_type")
    old = (
        "resume_parse",
        "resume_embed",
        "profile_embed",
        "job_parse",
        "job_embed",
        "match_batch",
    )
    values = ", ".join(f"'{item}'" for item in old)
    sql = f"ALTER TABLE processing_jobs ADD CONSTRAINT ck_processing_jobs_type CHECK (type IN ({values}))"
    op.execute(sql)
