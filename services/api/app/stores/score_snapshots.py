"""Scores as they were shown (rule 20): a score computed under an earlier version stays as it was.

Scores are computed on request from the point-in-time store, so the same date can read differently
later (a late revision, a new source decision, a new recipe). Each distinct live score served to
users is kept here with the scorecard and catalog versions it was computed with. The recipe is not
stored: a snapshot holds what users could see with the mechanism hidden (scores, confidence,
pending releases), whatever the disclosure switch was.
"""

import hashlib
import json
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.schemas.market import CountryScore
from app.stores.db import Base

# What is stored is what a user sees with the mechanism hidden.
EXCLUDED = {"indicators", "mechanism"}


class ScoreSnapshotRow(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8))
    as_of: Mapped[date] = mapped_column(Date)
    scorecard_version: Mapped[str] = mapped_column(String(16))
    catalog_version: Mapped[str] = mapped_column(String(16))
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_score_snapshots_lookup", "code", "as_of", "payload_hash", unique=True),
    )


class SnapshotStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, card: CountryScore, now: datetime | None = None) -> bool:
        """Keep this score if it differs from every one already kept for its code and date.
        Returns whether it was new. Only live scores with their versions are kept."""
        if card.data != "live" or card.as_of is None:
            return False
        if card.scorecard_version is None or card.catalog_version is None:
            return False
        payload = json.dumps(card.model_dump(mode="json", exclude=EXCLUDED), sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        known = self.session.scalar(
            select(ScoreSnapshotRow.id).where(
                ScoreSnapshotRow.code == card.code,
                ScoreSnapshotRow.as_of == card.as_of,
                ScoreSnapshotRow.payload_hash == digest,
            )
        )
        if known is not None:
            return False
        self.session.add(
            ScoreSnapshotRow(
                code=card.code,
                as_of=card.as_of,
                scorecard_version=card.scorecard_version,
                catalog_version=card.catalog_version,
                payload_hash=digest,
                payload=payload,
                shown_at=now or datetime.now(UTC),
            )
        )
        self.session.commit()
        return True

    def shown(self, code: str, as_of: date) -> list[dict]:
        """Every distinct score shown for a code and date, oldest first."""
        rows = self.session.scalars(
            select(ScoreSnapshotRow)
            .where(ScoreSnapshotRow.code == code, ScoreSnapshotRow.as_of == as_of)
            .order_by(ScoreSnapshotRow.shown_at, ScoreSnapshotRow.id)
        )
        return [{**json.loads(r.payload), "shownAt": r.shown_at.isoformat()} for r in rows]
