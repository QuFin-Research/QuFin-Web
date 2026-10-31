"""Point-in-time macro data.

Every observation is stored with the real-time period in which it was the published value,
the way ALFRED models vintages: a row is what the public knew about `period` from
`realtime_start` to `realtime_end` (inclusive). A revision closes the old row and opens a new
one. Asking "what was known on day D" is then a range filter, which keeps backtests and
scorecards free of look-ahead from later revisions.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, Text, delete, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.stores.db import Base, as_utc

# ALFRED's marker for "still the current value".
OPEN_END = date(9999, 12, 31)


class MacroSeriesRow(Base):
    __tablename__ = "macro_series"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(Text)
    units: Mapped[str] = mapped_column(String(255))
    frequency: Mapped[str] = mapped_column(String(32))
    seasonal_adjustment: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(2), index=True)
    dimension: Mapped[str] = mapped_column(String(16), index=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MacroObservationRow(Base):
    __tablename__ = "macro_observations"

    series_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("macro_series.id", ondelete="CASCADE"), primary_key=True
    )
    period: Mapped[date] = mapped_column(Date, primary_key=True)
    realtime_start: Mapped[date] = mapped_column(Date, primary_key=True)
    realtime_end: Mapped[date] = mapped_column(Date)
    # None where the source published "no value" for that vintage.
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_macro_observations_asof", "series_id", "realtime_start", "realtime_end"),
    )


@dataclass(frozen=True)
class SeriesMeta:
    id: str
    source: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    country: str
    dimension: str
    last_updated: datetime | None


@dataclass(frozen=True)
class Vintage:
    """One published value of one period, valid over [realtime_start, realtime_end]."""

    period: date
    realtime_start: date
    realtime_end: date
    value: float | None


@dataclass(frozen=True)
class SeriesSummary:
    meta: SeriesMeta
    ingested_at: datetime
    first_period: date | None
    last_period: date | None
    vintage_rows: int


def _meta(row: MacroSeriesRow) -> SeriesMeta:
    return SeriesMeta(
        id=row.id,
        source=row.source,
        title=row.title,
        units=row.units,
        frequency=row.frequency,
        seasonal_adjustment=row.seasonal_adjustment,
        country=row.country,
        dimension=row.dimension,
        last_updated=as_utc(row.last_updated) if row.last_updated else None,
    )


class MacroStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- writes (ingestion) ----------------------------------------------------------------

    def replace_series(self, meta: SeriesMeta, vintages: Iterable[Vintage]) -> int:
        """Store a series and its full vintage history, replacing what was there.

        ALFRED returns the complete history on every fetch, so a replace inside one
        transaction is both simple and idempotent. Returns the number of vintage rows.
        """
        rows = [
            MacroObservationRow(
                series_id=meta.id,
                period=v.period,
                realtime_start=v.realtime_start,
                realtime_end=v.realtime_end,
                value=v.value,
            )
            for v in vintages
        ]
        series = self.session.get(MacroSeriesRow, meta.id) or MacroSeriesRow(id=meta.id)
        series.source = meta.source
        series.title = meta.title
        series.units = meta.units
        series.frequency = meta.frequency
        series.seasonal_adjustment = meta.seasonal_adjustment
        series.country = meta.country
        series.dimension = meta.dimension
        series.last_updated = meta.last_updated
        series.ingested_at = datetime.now(UTC)
        self.session.add(series)
        self.session.flush()
        self.session.execute(
            delete(MacroObservationRow).where(MacroObservationRow.series_id == meta.id)
        )
        self.session.add_all(rows)
        self.session.commit()
        return len(rows)

    # --- reads -----------------------------------------------------------------------------

    def list_series(self) -> list[SeriesSummary]:
        stats = (
            select(
                MacroObservationRow.series_id,
                func.min(MacroObservationRow.period).label("first_period"),
                func.max(MacroObservationRow.period).label("last_period"),
                func.count().label("vintage_rows"),
            )
            .group_by(MacroObservationRow.series_id)
            .subquery()
        )
        result = self.session.execute(
            select(MacroSeriesRow, stats.c.first_period, stats.c.last_period, stats.c.vintage_rows)
            .outerjoin(stats, stats.c.series_id == MacroSeriesRow.id)
            .order_by(MacroSeriesRow.country, MacroSeriesRow.dimension, MacroSeriesRow.id)
        )
        return [
            SeriesSummary(
                meta=_meta(row),
                ingested_at=as_utc(row.ingested_at),
                first_period=first,
                last_period=last,
                vintage_rows=count or 0,
            )
            for row, first, last, count in result
        ]

    def get_series(self, series_id: str) -> SeriesMeta | None:
        row = self.session.get(MacroSeriesRow, series_id)
        return _meta(row) if row else None

    def as_of(
        self,
        series_id: str,
        as_of: date | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> Sequence[Vintage]:
        """The series as it was published on `as_of` (latest values when None)."""
        query = select(MacroObservationRow).where(MacroObservationRow.series_id == series_id)
        if as_of is None:
            query = query.where(MacroObservationRow.realtime_end == OPEN_END)
        else:
            query = query.where(
                MacroObservationRow.realtime_start <= as_of,
                MacroObservationRow.realtime_end >= as_of,
            )
        if start is not None:
            query = query.where(MacroObservationRow.period >= start)
        if end is not None:
            query = query.where(MacroObservationRow.period <= end)
        rows = self.session.scalars(query.order_by(MacroObservationRow.period))
        return [_vintage(r) for r in rows]

    def revisions(self, series_id: str, period: date) -> Sequence[Vintage]:
        """Every published value of one period, first release first."""
        rows = self.session.scalars(
            select(MacroObservationRow)
            .where(
                MacroObservationRow.series_id == series_id,
                MacroObservationRow.period == period,
            )
            .order_by(MacroObservationRow.realtime_start)
        )
        return [_vintage(r) for r in rows]


def _vintage(row: MacroObservationRow) -> Vintage:
    return Vintage(
        period=row.period,
        realtime_start=row.realtime_start,
        realtime_end=row.realtime_end,
        value=row.value,
    )
