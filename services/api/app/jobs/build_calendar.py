"""Build the economic calendar from what the point-in-time store holds (ADR 0007).

For every weekly, monthly, quarterly or annual series (daily rates and prices are not releases):
one released event per period first published in the last year (release date, first print, the
previous period's value as known on that day), and one scheduled event for the next period, dated
by the series' usual release lag (rule 9: derived, erring late). Consensus and surprise are never
produced here: they stay empty until a licensed feed fills them (rule 8), and a row's consensus is
kept when this job runs again.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.freshness import assess, frequency_code
from app.domain.surprise import surprise, surprise_score
from app.stores.macro import MacroObservationRow, MacroSeriesRow, MacroStore
from app.stores.taxonomy import EconomicEventRow

WINDOW_DAYS = 365
# One period before the window, so the first event in it has a previous value.
BACK_DAYS = WINDOW_DAYS + 120


@dataclass(frozen=True)
class CalendarResult:
    released: int
    scheduled: int


def next_period(period: date, frequency: str) -> date:
    code = frequency_code(frequency)
    if code == "D":
        return period + timedelta(days=1)
    if code in ("W", "B"):
        return period + timedelta(days=7 if code == "W" else 14)
    months = {"M": 1, "Q": 3, "S": 6, "A": 12}[code]
    index = period.year * 12 + period.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _value_known_on(rows: list[MacroObservationRow], day: date) -> float | None:
    for r in rows:
        if r.realtime_start <= day <= r.realtime_end:
            return r.value
    return None


def _upsert(
    session: Session, existing: dict[tuple[str, date], EconomicEventRow], **fields
) -> EconomicEventRow:
    key = (fields["series_id"], fields["period"])
    row = existing.get(key)
    if row is None:
        row = EconomicEventRow(**fields)
        existing[key] = row
    else:  # consensus fields are not touched: they come from a different feed
        for name, value in fields.items():
            setattr(row, name, value)
    session.add(row)
    return row


def build(session: Session, today: date) -> CalendarResult:
    store = MacroStore(session)
    since = today - timedelta(days=WINDOW_DAYS)
    lag_releases = store.first_releases(today - timedelta(days=366 * 2))
    existing = {(e.series_id, e.period): e for e in session.scalars(select(EconomicEventRow))}
    released = scheduled = 0
    for series in session.scalars(select(MacroSeriesRow)):
        if frequency_code(series.frequency) == "D":
            continue  # daily rates and prices are not scheduled releases
        rows_by_period: dict[date, list[MacroObservationRow]] = defaultdict(list)
        for r in session.scalars(
            select(MacroObservationRow)
            .where(
                MacroObservationRow.series_id == series.id,
                MacroObservationRow.period >= since - timedelta(days=BACK_DAYS - WINDOW_DAYS),
            )
            .order_by(MacroObservationRow.period, MacroObservationRow.realtime_start)
        ):
            rows_by_period[r.period].append(r)
        periods = sorted(rows_by_period)
        for i, period in enumerate(periods):
            first = rows_by_period[period][0]
            if first.realtime_start < since or first.realtime_start > today:
                continue
            previous = (
                _value_known_on(rows_by_period[periods[i - 1]], first.realtime_start)
                if i > 0
                else None
            )
            row = _upsert(
                session,
                existing,
                series_id=series.id,
                period=period,
                release_date=first.realtime_start,
                status="released",
                previous_value=previous,
                actual_value=first.value,
            )
            history = [
                s
                for e in existing.values()
                if e.series_id == series.id
                and e is not row
                and (s := surprise(e.actual_value, e.consensus_estimate)) is not None
            ]
            row.surprise_score = surprise_score(row.actual_value, row.consensus_estimate, history)
            released += 1

        last = series.last_period
        if last is None:
            continue
        lags = [
            (rel - p).days for p, rel in lag_releases.get(series.id, {}).items() if rel <= today
        ]
        fresh = assess(
            title=series.title,
            frequency=series.frequency,
            last_period=last,
            release_lags=lags,
            today=today,
        )
        if fresh.next_due is None:
            continue
        upcoming = next_period(last, series.frequency)
        if (series.id, upcoming) in existing and existing[
            (series.id, upcoming)
        ].status == "released":
            continue
        last_rows = rows_by_period.get(last)
        _upsert(
            session,
            existing,
            series_id=series.id,
            period=upcoming,
            release_date=fresh.next_due,
            status="scheduled",
            previous_value=last_rows[-1].value if last_rows else None,
            actual_value=None,
            surprise_score=None,
        )
        scheduled += 1
    session.commit()
    return CalendarResult(released, scheduled)
