"""PostgreSQL fixtures for domain persistence and authentication tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "8192"
os.environ.setdefault("EMBEDDING_BACKEND", "hashing")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import reset_rate_limiter

get_settings.cache_clear()

BACKEND_ROOT = Path(__file__).resolve().parents[1]
AUTH_ORIGIN = "http://localhost:3000"


def _ensure_database(url_str: str) -> None:
    url = make_url(url_str)
    if url.database is None:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")
    admin = url.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    engine.dispose()


def _alembic_config(url_str: str) -> Config:
    os.environ["ALEMBIC_DATABASE_URL"] = url_str
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url_str.replace("%", "%%"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_settings().test_database_url


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Generator[Engine, None, None]:
    _ensure_database(test_database_url)
    command.upgrade(_alembic_config(test_database_url), "head")
    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def seeded_ontology(db_session: Session):
    from app.modules.ontology.seed import seed_ontology

    return seed_ontology(db_session)


@pytest.fixture
def db_session(migrated_engine: Engine) -> Generator[Session, None, None]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def blob_store(tmp_path):
    from app.modules.documents.storage import LocalBlobStore

    return LocalBlobStore(tmp_path / "blobs")


@pytest.fixture
def client(db_session: Session, blob_store) -> Generator[TestClient, None, None]:
    from app.main import app
    from app.modules.documents.storage import get_blob_store

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_blob_store] = lambda: blob_store
    reset_rate_limiter()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(csrf_token: str | None = None, access_token: str | None = None) -> dict[str, str]:
    headers = {"Origin": AUTH_ORIGIN}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers
