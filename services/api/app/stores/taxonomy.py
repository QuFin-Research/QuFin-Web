"""Country dimension and the economic calendar (ADR 0007).

`dim_country_taxonomy` holds what a country is (codes, currency, central bank, blocs); its rows
come from `app/data/taxonomy.py`, the single source of truth, and are refreshed by
`python -m app.cli sync-taxonomy`. `fact_economic_calendar` holds one row per series and period:
when it is (or was) released, the value before, the consensus when a licensed feed supplies one,
the first-print value, and the surprise computed from them. Nothing here is invented: consensus
and surprise stay empty until a licensed feed fills them (rule 8).
"""

from collections.abc import Sequence
from datetime import date, time

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.stores.db import Base
from app.stores.macro import MacroSeriesRow


class CountryRow(Base):
    __tablename__ = "dim_country_taxonomy"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    iso2: Mapped[str] = mapped_column(String(2), unique=True)
    name: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3))
    central_bank: Mapped[str] = mapped_column(Text)
    g7: Mapped[bool] = mapped_column(Boolean, default=False)
    g20: Mapped[bool] = mapped_column(Boolean, default=False)
    gcc: Mapped[bool] = mapped_column(Boolean, default=False)
    em: Mapped[bool] = mapped_column(Boolean, default=False)


class EconomicEventRow(Base):
    __tablename__ = "fact_economic_calendar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("macro_series.id", ondelete="CASCADE")
    )
    period: Mapped[date] = mapped_column(Date)
    # The date of the release: the first publication of the period when it has happened,
    # else the date derived from the series' usual lag (rule 9: derived, erring late).
    release_date: Mapped[date] = mapped_column(Date)
    # Time of day (UTC) once the source's release time is recorded; empty until then.
    release_time_utc: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(12))  # "released" or "scheduled"
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    consensus_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    consensus_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # The first print, as published at the release (later revisions are vintages, not this).
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    surprise_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("series_id", "period", name="uq_calendar_series_period"),
        Index("ix_calendar_release_date", "release_date", "series_id"),
    )


def calendar_window(
    session: Session,
    first: date,
    last: date,
    *,
    pillar: str | None = None,
    iso2: str | None = None,
    limit: int = 1000,
) -> Sequence[tuple[EconomicEventRow, MacroSeriesRow]]:
    """Events released between two days, soonest first (served by ix_calendar_release_date)."""
    query = (
        select(EconomicEventRow, MacroSeriesRow)
        .join(MacroSeriesRow, MacroSeriesRow.id == EconomicEventRow.series_id)
        .where(EconomicEventRow.release_date >= first, EconomicEventRow.release_date <= last)
        .order_by(EconomicEventRow.release_date, EconomicEventRow.series_id)
        .limit(limit)
    )
    if pillar:
        query = query.where(MacroSeriesRow.pillar == pillar)
    if iso2:
        query = query.where(MacroSeriesRow.country == iso2)
    return [(event, series) for event, series in session.execute(query)]
