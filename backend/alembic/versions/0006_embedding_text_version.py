"""Add embedding text version and chunk type.

Revision ID: 0006_embedding_text_version
Revises: 0005_ontology_graph_snapshot
Create Date: 2026-08-27

Does not modify 0001–0005. Does not fix a vector dimension.
Embeddings remain unconstrained VECTOR until the encoder dimension is verified at runtime.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006_embedding_text_version"
down_revision: str | None = "0005_ontology_graph_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_TYPES = (
    "profile",
    "job",
    "project",
    "experience",
    "resume_chunk",
    "job_requirement",
    "skill",
)

JOB_TYPES = (
    "resume_parse",
    "resume_nlp",
    "resume_embed",
    "profile_embed",
    "job_parse",
    "job_embed",
    "project_embed",
    "experience_embed",
    "match_batch",
)


def _columns(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table)}


def _uniques(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_unique_constraints(table) if item.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = _columns(inspector, "embeddings")
    if "chunk_type" not in columns:
        op.add_column(
            "embeddings",
            sa.Column("chunk_type", sa.String(length=64), nullable=False, server_default="full"),
        )
    inspector = inspect(bind)
    columns = _columns(inspector, "embeddings")
    if "embedding_text_version" not in columns:
        op.add_column(
            "embeddings",
            sa.Column(
                "embedding_text_version",
                sa.String(length=64),
                nullable=False,
                server_default="embedding-text-v1",
            ),
        )
    uniques = _uniques(inspect(bind), "embeddings")
    if "uq_embeddings_owner_model" in uniques:
        op.drop_constraint("uq_embeddings_owner_model", "embeddings", type_="unique")
    uniques = _uniques(inspect(bind), "embeddings")
    if "uq_embeddings_owner_model_text" not in uniques:
        op.create_unique_constraint(
            "uq_embeddings_owner_model_text",
            "embeddings",
            [
                "owner_type",
                "owner_id",
                "chunk_type",
                "model_name",
                "model_version",
                "embedding_text_version",
            ],
        )
    op.execute("ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS ck_embeddings_owner_type")
    owners = ", ".join(f"'{item}'" for item in OWNER_TYPES)
    op.execute(
        "ALTER TABLE embeddings ADD CONSTRAINT ck_embeddings_owner_type "
        f"CHECK (owner_type IN ({owners}))"
    )
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS ck_processing_jobs_type")
    values = ", ".join(f"'{item}'" for item in JOB_TYPES)
    op.execute(
        "ALTER TABLE processing_jobs ADD CONSTRAINT ck_processing_jobs_type "
        f"CHECK (type IN ({values}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS ck_processing_jobs_type")
    old_jobs = (
        "resume_parse",
        "resume_nlp",
        "resume_embed",
        "profile_embed",
        "job_parse",
        "job_embed",
        "match_batch",
    )
    values = ", ".join(f"'{item}'" for item in old_jobs)
    op.execute(
        "ALTER TABLE processing_jobs ADD CONSTRAINT ck_processing_jobs_type "
        f"CHECK (type IN ({values}))"
    )
    op.execute("ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS ck_embeddings_owner_type")
    old_owners = (
        "profile",
        "job",
        "project",
        "experience",
        "resume_chunk",
        "skill",
    )
    owners = ", ".join(f"'{item}'" for item in old_owners)
    op.execute(
        "ALTER TABLE embeddings ADD CONSTRAINT ck_embeddings_owner_type "
        f"CHECK (owner_type IN ({owners}))"
    )
    uniques = _uniques(inspect(op.get_bind()), "embeddings")
    if "uq_embeddings_owner_model_text" in uniques:
        op.drop_constraint("uq_embeddings_owner_model_text", "embeddings", type_="unique")
    uniques = _uniques(inspect(op.get_bind()), "embeddings")
    if "uq_embeddings_owner_model" not in uniques:
        op.create_unique_constraint(
            "uq_embeddings_owner_model",
            "embeddings",
            ["owner_type", "owner_id", "model_name", "model_version"],
        )
    columns = _columns(inspect(op.get_bind()), "embeddings")
    if "embedding_text_version" in columns:
        op.drop_column("embeddings", "embedding_text_version")
    columns = _columns(inspect(op.get_bind()), "embeddings")
    if "chunk_type" in columns:
        op.drop_column("embeddings", "chunk_type")
