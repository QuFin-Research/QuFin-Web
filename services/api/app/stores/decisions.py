"""Decision journal persistence (SQLAlchemy; SQLite now, Postgres later via QUFIN_DATABASE_URL).

Decisions are not yet scoped to a user: that arrives with authentication.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.schemas.decisions import Decision, DecisionBacktestSummary, DecisionCreate


class Base(DeclarativeBase):
    pass


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    direction: Mapped[str] = mapped_column(String(5))
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    risk_pct: Mapped[float] = mapped_column(Float)
    max_hold_days: Mapped[int] = mapped_column(Integer)
    signal_prob_up: Mapped[float] = mapped_column(Float)
    backtest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    def to_schema(self) -> Decision:
        created = self.created_at
        if created.tzinfo is None:  # SQLite drops the offset; values are stored in UTC
            created = created.replace(tzinfo=UTC)
        return Decision(
            id=self.id,
            symbol=self.symbol,
            direction=self.direction,  # type: ignore[arg-type]
            entry=self.entry,
            stop=self.stop,
            target=self.target,
            risk_pct=self.risk_pct,
            max_hold_days=self.max_hold_days,
            signal_prob_up=self.signal_prob_up,
            backtest=DecisionBacktestSummary.model_validate_json(self.backtest_json)
            if self.backtest_json
            else None,
            note=self.note,
            created_at=created,
        )


def make_engine(url: str) -> Engine:
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


class DecisionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Decision]:
        rows = self.session.scalars(select(DecisionRow).order_by(DecisionRow.created_at.desc()))
        return [row.to_schema() for row in rows]

    def add(self, data: DecisionCreate) -> Decision:
        row = DecisionRow(
            id=str(uuid.uuid4()),
            symbol=data.symbol,
            direction=data.direction,
            entry=data.entry,
            stop=data.stop,
            target=data.target,
            risk_pct=data.risk_pct,
            max_hold_days=data.max_hold_days,
            signal_prob_up=data.signal_prob_up,
            backtest_json=json.dumps(data.backtest.model_dump(by_alias=True))
            if data.backtest
            else None,
            note=data.note,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        self.session.commit()
        return row.to_schema()

    def delete(self, decision_id: str) -> bool:
        row = self.session.get(DecisionRow, decision_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.commit()
        return True
