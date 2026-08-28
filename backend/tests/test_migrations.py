from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import _alembic_config, _ensure_database


def test_alembic_upgrade_downgrade_upgrade_on_clean_database() -> None:
    url = "postgresql+psycopg://recs:recs@localhost:5432/recs_migrate"
    _ensure_database(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        ext = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
        tables = inspect(conn).get_table_names()
    engine.dispose()
    assert ext == "vector"
    assert "users" in tables
    assert "skill_relations" in tables
    assert "match_runs" in tables
    assert "ml_training_runs" in tables
