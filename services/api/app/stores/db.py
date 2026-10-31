"""Database engine and sessions (SQLAlchemy; SQLite locally, Postgres via QUFIN_DATABASE_URL).

The schema is owned by the Alembic migrations in `migrations/`; see app/stores/migrate.py.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    """Import every model module so its tables are registered on Base.metadata."""
    from app.stores import decisions, macro, users  # noqa: F401


def as_utc(value: datetime) -> datetime:
    """SQLite drops the offset; every timestamp is stored in UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # one shared in-memory database
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def create_all(engine: Engine) -> None:
    """Create every table directly from the models. For tests only; use migrations elsewhere."""
    import_models()
    Base.metadata.create_all(engine)


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


def session_scope() -> Session:
    """A session for scripts and jobs (use as a context manager)."""
    return _session_factory()()


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    with _session_factory()() as session:
        yield session
