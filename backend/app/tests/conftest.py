from __future__ import annotations

from pathlib import Path
import sys
from typing import Generator

# Ensure `backend` directory is in sys.path so `app.*` imports resolve in all environments
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db
from app.config import settings
from app.main import app as fastapi_app
import app.models  # noqa: F401 - Ensures all ORM models are loaded

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI_PATH = PROJECT_ROOT / "backend" / "alembic.ini"


# Test-only SQLite DDL adapters so Alembic migrations and ORM tests run in complete
# isolation without touching any existing PostgreSQL database when TEST_DATABASE_URL is unset.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw) -> str:
    return "JSON"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(element, compiler, **kw) -> str:
    return "TEXT"


def build_alembic_config(database_url: str) -> AlembicConfig:
    """Create an Alembic Config object targeting a specific isolated test database URL."""
    cfg = AlembicConfig(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return cfg


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="session")
def test_database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Resolve an isolated test database URL; never targets the user's configured DATABASE_URL."""
    configured_test_url = settings.test_database_url
    if configured_test_url:
        if configured_test_url == settings.sync_database_url:
            raise RuntimeError(
                "TEST_DATABASE_URL must not match DATABASE_URL to protect existing databases."
            )
        return configured_test_url

    db_file = tmp_path_factory.mktemp("coursepilot_test_db") / "test_coursepilot.sqlite3"
    return f"sqlite:///{db_file.as_posix()}"


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Generator[Engine, None, None]:
    """Create an isolated test engine and initialize schema via Alembic migrations."""
    engine = create_engine(test_database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    alembic_cfg = build_alembic_config(test_database_url)
    command.upgrade(alembic_cfg, "head")

    try:
        yield engine
    finally:
        command.downgrade(alembic_cfg, "base")
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Provide an isolated transactional session rolled back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to the isolated transactional test DB session."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()

