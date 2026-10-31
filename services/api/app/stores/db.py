"""Database engine and sessions (SQLAlchemy; SQLite now, Postgres later via QUFIN_DATABASE_URL).

Tables are created on startup with `create_all`. Schema changes need Alembic migrations before
any real data is stored; until then, delete the local SQLite file after a schema change.
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


def as_utc(value: datetime) -> datetime:
    """SQLite drops the offset; every timestamp is stored in UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def make_engine(url: str) -> Engine:
    # Import the models so their tables are registered on Base.metadata.
    from app.stores import decisions, users  # noqa: F401

    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # one shared in-memory database
        engine = create_engine(url, **kwargs)
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(make_engine(get_settings().database_url), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    with _session_factory()() as session:
        yield session
