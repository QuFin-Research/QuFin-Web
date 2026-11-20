"""When each period of a staged candidate was first read (rule 38, "Earliest").

A candidate source is loaded without being served so its release timing can be measured over a
release cycle. The vintage store dates a new period by the earlier of its derived release date and
the day it was seen, which errs late for a late source; the measurement needs the day it was
actually first read. This table keeps that day per period. Periods already there when a candidate is
first loaded are marked `bootstrap`: they were published before QuFin looked, so they say nothing
about timing.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Boolean, Date, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.stores.db import Base


class CandidateSightingRow(Base):
    __tablename__ = "candidate_sightings"

    series_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    period: Mapped[date] = mapped_column(Date, primary_key=True)
    first_seen: Mapped[date] = mapped_column(Date)
    bootstrap: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_candidate_sightings_series", "series_id", "first_seen"),)


@dataclass(frozen=True)
class Sighting:
    series_id: str
    period: date
    first_seen: date
    bootstrap: bool


class CandidateStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self, series_id: str, periods: Iterable[date], today: date, *, bootstrap: bool
    ) -> int:
        """Note the periods not seen before; returns how many were new."""
        known = set(
            self.session.scalars(
                select(CandidateSightingRow.period).where(
                    CandidateSightingRow.series_id == series_id
                )
            )
        )
        new = [p for p in sorted(set(periods)) if p not in known]
        self.session.add_all(
            CandidateSightingRow(
                series_id=series_id, period=p, first_seen=today, bootstrap=bootstrap
            )
            for p in new
        )
        self.session.commit()
        return len(new)

    def sightings(self, series_id: str) -> list[Sighting]:
        rows = self.session.scalars(
            select(CandidateSightingRow)
            .where(CandidateSightingRow.series_id == series_id)
            .order_by(CandidateSightingRow.period)
        )
        return [Sighting(r.series_id, r.period, r.first_seen, r.bootstrap) for r in rows]

    def measurable(self, series_id: str) -> list[Sighting]:
        """The periods first read after QuFin started looking: the ones that time the source."""
        return [s for s in self.sightings(series_id) if not s.bootstrap]
