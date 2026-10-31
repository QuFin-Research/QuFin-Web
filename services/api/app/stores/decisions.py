"""Decision journal persistence. Every decision belongs to one user."""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.schemas.decisions import Decision, DecisionBacktestSummary, DecisionCreate
from app.stores.db import Base, as_utc


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
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
            created_at=as_utc(self.created_at),
        )


class DecisionStore:
    """Reads and writes one user's decisions; other users' rows are invisible to it."""

    def __init__(self, session: Session, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def list(self) -> list[Decision]:
        rows = self.session.scalars(
            select(DecisionRow)
            .where(DecisionRow.user_id == self.user_id)
            .order_by(DecisionRow.created_at.desc())
        )
        return [row.to_schema() for row in rows]

    def add(self, data: DecisionCreate) -> Decision:
        row = DecisionRow(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
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
        if row is None or row.user_id != self.user_id:
            return False
        self.session.delete(row)
        self.session.commit()
        return True
