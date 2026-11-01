"""How much a series moved: the change measures shown with every series and used for momentum.

The measure follows the series (catalog `change`): percent change for quantities and price
indexes, change in the series' own units for rates, spreads, ratios and indexes that can be
zero or negative. A series the source already publishes as a change is never changed again.

Changes are taken within one vintage: both values as they were published on the same date,
so a revision never shows up as a move. Daily and weekly series are compared as 28-day
averages, which keeps their head start (the latest week counts at once) without the noise of a
single day.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.data.macro_catalog import ChangeKind
from app.domain.freshness import frequency_code

WINDOW_DAYS = 28


@dataclass(frozen=True)
class Change:
    horizon: str  # "1m", "3m", "1y" (q/q and y/y for quarterly series)
    value: float
    unit: str  # "%", "% ann." or "pt"


def _pct(new: float, old: float, annualise: float = 1.0) -> float | None:
    if old <= 0 or new <= 0:
        return None
    return ((new / old) ** annualise - 1) * 100


def _measure(
    new: float, old: float, kind: ChangeKind, annualise: float = 1.0
) -> tuple[float, str] | None:
    if kind == "diff":
        return new - old, "pt"
    value = _pct(new, old, annualise)
    if value is None:
        return None
    return value, ("% ann." if annualise != 1.0 else "%")


def _window_mean(points: Sequence[tuple[date, float]], end: date) -> float | None:
    values = [v for p, v in points if end - timedelta(days=WINDOW_DAYS) < p <= end]
    return statistics.fmean(values) if values else None


def change_measures(
    points: Sequence[tuple[date, float | None]], frequency: str, kind: ChangeKind
) -> list[Change]:
    """Latest moves over one month, three months (annualised for percent) and a year."""
    values = [(p, v) for p, v in points if v is not None]
    if len(values) < 2:
        return []
    code = frequency_code(frequency)
    result: list[Change] = []

    if code in ("D", "W", "B"):
        last = values[-1][0]
        now = _window_mean(values, last)
        for horizon, days, annualise in (("1m", 28, 1.0), ("3m", 91, 365 / 91), ("1y", 364, 1.0)):
            then = _window_mean(values, last - timedelta(days=days))
            if now is None or then is None:
                continue
            m = _measure(now, then, kind, annualise if kind == "pct" else 1.0)
            if m:
                result.append(Change(horizon, round(m[0], 3), m[1]))
        return result

    by_period = dict(values)
    last_period, last_value = values[-1]

    def back(months: int) -> float | None:
        y, m = divmod(last_period.month - 1 - months, 12)
        return by_period.get(date(last_period.year + y, m + 1, 1))

    steps = (
        (("q/q", 3, 4.0), ("y/y", 12, 1.0))
        if code == "Q"
        else (("1m", 1, 1.0), ("3m", 3, 4.0), ("1y", 12, 1.0))
    )
    for horizon, months, annualise in steps:
        old = back(months)
        if old is None:
            continue
        m = _measure(last_value, old, kind, annualise if kind == "pct" else 1.0)
        if m:
            result.append(Change(horizon, round(m[0], 3), m[1]))
    return result
