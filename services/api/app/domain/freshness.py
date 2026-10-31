"""Release-schedule and timeliness rules for every data series QuFin relies on.

QuFin rule: data that is overdue, discontinued or delayed in a way the catalog does not
account for must not feed signals, scorecards or backtests as if it were current. Every source
is checked against its own schedule after each ingest, and the API reports the result next to
the data.

Schedule. A series is due one period after its latest observation plus its usual release lag
(the median gap between a period and the source's first release, measured from the stored
vintages) plus any delay FRED adds on top of the source (declared in the catalog). Past that
date plus a grace period for holidays and calendar drift, it is overdue.

Timeliness. Data that only reaches us long after its period ended says less about now, so a
series' weight halves for every HALF_LIFE_DAYS between the end of its period and the day we
can read it (source lag plus FRED's delay). Weekly claims and daily yields keep full weight;
a licensing-delayed survey or a two-month-old orders report counts for less. Unusable series
weigh nothing.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Status = Literal["ok", "overdue", "discontinued", "review"]

# Keyed by the first letter of FRED's frequency name ("Daily", "Weekly, Ending Friday", ...).
STEP_DAYS = {"D": 1, "W": 7, "B": 14, "M": 31, "Q": 92, "S": 183, "A": 366}
GRACE_DAYS = {"D": 5, "W": 7, "B": 7, "M": 14, "Q": 30, "S": 45, "A": 60}
HALF_LIFE_DAYS = 60


@dataclass(frozen=True)
class Freshness:
    status: Status
    next_due: date | None
    typical_lag_days: int
    days_overdue: int
    reason: str

    @property
    def usable(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class Timeliness:
    source_lag_days: int
    fred_delay_days: int
    days_after_period_end: int
    weight: float


def frequency_code(frequency: str) -> str:
    code = frequency.strip()[:1].upper()
    if code not in STEP_DAYS:
        raise ValueError(f"Unknown release frequency: {frequency!r}")
    return code


def _median(values: Sequence[int]) -> int:
    return int(statistics.median(values)) if values else 0


def assess(
    *,
    title: str,
    frequency: str,
    last_period: date | None,
    release_lags: Sequence[int],
    today: date,
    fred_delay_days: int = 0,
    review_reason: str | None = None,
) -> Freshness:
    lag = _median(release_lags)
    if "DISCONTINUED" in title.upper():
        return Freshness("discontinued", None, lag, 0, "The source marks this series discontinued")
    if review_reason:
        return Freshness("review", None, lag, 0, review_reason)
    if last_period is None:
        return Freshness("overdue", None, lag, 0, "No observations stored")
    code = frequency_code(frequency)
    due = last_period + timedelta(days=STEP_DAYS[code] + lag + fred_delay_days)
    late = (today - due).days
    if late > GRACE_DAYS[code]:
        return Freshness(
            "overdue", due, lag, late, f"Next release was due {due.isoformat()}, {late} days ago"
        )
    return Freshness("ok", due, lag, 0, f"Next release due around {due.isoformat()}")


def timeliness(
    frequency: str, release_lags: Sequence[int], fred_delay_days: int, usable: bool
) -> Timeliness:
    lag = _median(release_lags)
    after_end = max(0, lag + fred_delay_days - STEP_DAYS[frequency_code(frequency)])
    weight = round(0.5 ** (after_end / HALF_LIFE_DAYS), 2) if usable else 0.0
    return Timeliness(lag, fred_delay_days, after_end, weight)
