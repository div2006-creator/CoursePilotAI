from contextlib import contextmanager
from datetime import datetime, timezone
import logging
from typing import Generator

from pgvector.sqlalchemy import Vector
from sqlalchemy import Engine, MetaData, create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


# Allow PostgreSQL-specific column types (JSONB, pgvector) to compile cleanly
# when running locally against SQLite (e.g., dev fallback or isolated tests).
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw) -> str:
    return "JSON"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(element, compiler, **kw) -> str:
    return "TEXT"


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Deterministic naming convention for constraints and indexes (Alembic best practice)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class DatabaseConnectionError(RuntimeError):
    """Raised when the application cannot establish a database connection."""


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base for all CoursePilot AI ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utc_now() -> datetime:
    """Return a timezone-aware current UTC timestamp."""
    return datetime.now(timezone.utc)


def create_db_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Create a configured SQLAlchemy 2.0 engine with health pre-pinging."""
    url = database_url or settings.sync_database_url
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": echo,
    }
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 1800,
            }
        )
    created_engine = create_engine(url, **engine_kwargs)
    if created_engine.dialect.name == "sqlite":
        event.listen(created_engine, "connect", _enable_sqlite_foreign_keys)
    return created_engine


# Primary database engine configured from DATABASE_URL / environment settings
engine = create_db_engine(settings.sync_database_url, echo=False)

# Thread-local database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session with rollback-on-error and guaranteed cleanup."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database session error; transaction rolled back: %s", exc)
        raise
    finally:
        db.close()


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Transactional context manager for scripts, migrations, and background jobs."""
    factory = session_factory or SessionLocal
    session = factory()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Transaction failed and was rolled back: %s", exc)
        raise
    finally:
        session.close()


def check_database_connection(
    db_engine: Engine | None = None,
    *,
    raise_on_error: bool = False,
) -> tuple[bool, str | None]:
    """Verify database connectivity by executing a lightweight SELECT 1 probe."""
    target_engine = db_engine or engine
    try:
        with target_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except (OperationalError, SQLAlchemyError) as exc:
        error_message = f"Database connection failed: {exc}"
        logger.error(error_message)
        if raise_on_error:
            raise DatabaseConnectionError(error_message) from exc
        return False, error_message
