"""Put series of different release frequencies on one frequency, then measure change (Rules D, E).

Series are compared at the lowest frequency they share: weekly is aggregated to monthly when one
selected series is monthly, and nothing is ever up-sampled. A period is only formed from a
complete bucket (no half-finished month is shown as a month). How a bucket collapses to one value
depends on what the series is:

- stock or level (a balance, a count of jobs, an amount outstanding): the value at period end;
- rate or index (a percentage, a ratio, a price index): the average over the period;
- flow (jobless claims in a week, a trade balance in a month): the sum over the period.

`PoC` is the change from one display period to the previous one: week, month, quarter, half-year
or year over the same step. A series that is a rate or spread changes in points, never percent
(rules 13 and 22); one the source already publishes as a change is not changed again.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from typing import Literal

Frequency = Literal["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"]
FREQUENCIES: tuple[Frequency, ...] = (
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "semi_annual",
    "annual",
)
RANK: dict[str, int] = {f: i for i, f in enumerate(FREQUENCIES)}
LABEL: dict[str, str] = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "semi_annual": "Semi-Annual",
    "annual": "Annual",
}
# What the change over one display period is called.
POC_NAME: dict[str, str] = {
    "daily": "Day-over-Day",
    "weekly": "Week-over-Week",
    "monthly": "Month-over-Month",
    "quarterly": "Quarter-over-Quarter",
    "semi_annual": "Half-over-Half",
    "annual": "Year-over-Year",
}
MAX_COUNTRIES = 10

Aggregation = Literal["end", "mean", "sum"]
# Series whose period value is a quantity accumulated over the period (never a level or a rate).
FLOW_CONCEPTS = frozenset(
    {
        "initial_jobless_claims",
        "trade_balance",
        "budget_balance",
        "government_interest_expense",
        "current_account",
    }
)
_AVERAGED_KINDS = frozenset({"rate_percent", "ratio", "index", "price_per_unit"})


def native_frequency(text: str) -> Frequency:
    """The frequency a source states ("Weekly, Ending Friday" is weekly)."""
    head = text.strip().lower()
    for name, key in (
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("monthly", "monthly"),
        ("quarterly", "quarterly"),
        ("semiannual", "semi_annual"),
        ("semi-annual", "semi_annual"),
        ("annual", "annual"),
    ):
        if head.startswith(name):
            return key  # type: ignore[return-value]
    raise ValueError(f"unknown frequency: {text!r}")


def adjustment_tag(text: str) -> Literal["SA", "NSA", "OTHER"]:
    """`SA` or `NSA` as the source states it (Rule B). Other treatments (for example the OECD's
    amplitude adjustment) are not called seasonal adjustment: they stay `OTHER`, with the text."""
    lowered = text.lower()
    if lowered.startswith("not seasonally") or lowered.startswith("not adjusted"):
        return "NSA"
    if lowered.startswith("seasonally"):
        return "SA"
    return "OTHER"


def aggregation_for(unit_kind: str | None, concept: str | None) -> Aggregation:
    if concept in FLOW_CONCEPTS:
        return "sum"
    if unit_kind in _AVERAGED_KINDS:
        return "mean"
    return "end"


@dataclass(frozen=True)
class Allowed:
    frequencies: list[Frequency]
    common: Frequency  # the lowest frequency every series has
    limiting: str | None  # the series that sets it, when any series is slower than the rest
    notice: str | None


def allowed_frequencies(natives: Sequence[tuple[str, Frequency]]) -> Allowed:
    """Frequencies every series can be shown at: its own and anything slower (Rule G).

    `natives` pairs a label (for the notice) with the series' own frequency.
    """
    if not natives:
        return Allowed(list(FREQUENCIES), "daily", None, None)
    label, slowest = max(natives, key=lambda n: RANK[n[1]])
    allowed = [f for f in FREQUENCIES if RANK[f] >= RANK[slowest]]
    if slowest == "daily":
        return Allowed(allowed, slowest, None, None)
    return Allowed(allowed, slowest, label, _restriction(allowed, label, slowest))


def _restriction(allowed: list[Frequency], label: str, slowest: Frequency) -> str:
    names = [LABEL[f] for f in allowed]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return (
        f"Only {listed} comparisons available: constrained by {label} ({LABEL[slowest].lower()})."
    )


def bucket_start(day: date, freq: Frequency) -> date:
    if freq == "daily":
        return day
    if freq == "weekly":
        return day - timedelta(days=day.weekday())
    if freq == "monthly":
        return day.replace(day=1)
    if freq == "quarterly":
        return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)
    if freq == "semi_annual":
        return date(day.year, 1 if day.month <= 6 else 7, 1)
    return date(day.year, 1, 1)


def bucket_end(start: date, freq: Frequency) -> date:
    """The last day of the bucket that starts on `start`."""
    if freq == "daily":
        return start
    if freq == "weekly":
        return start + timedelta(days=6)
    months = {"monthly": 1, "quarterly": 3, "semi_annual": 6, "annual": 12}[freq]
    total = start.year * 12 + start.month - 1 + months
    return date(total // 12, total % 12 + 1, 1) - timedelta(days=1)


# Months a native monthly or quarterly observation covers, so a bucket is complete only when every
# observation that belongs in it is present.
_MONTHS = {"monthly": 1, "quarterly": 3, "semi_annual": 6, "annual": 12}
# For daily and weekly series the last observation of a closed bucket sits within this many days
# of its end (a weekend or a week-ending day).
_TAIL_DAYS = {"daily": 4, "weekly": 7}


@dataclass(frozen=True)
class Obs:
    period: date
    value: float


def aggregate(
    points: Sequence[Obs], native: Frequency, target: Frequency, how: Aggregation
) -> list[Obs]:
    """The series at `target`. Equal frequency passes through; a faster target is refused.

    Incomplete buckets are dropped (the current, unfinished month is not a month yet).
    """
    ordered = sorted(points, key=lambda p: p.period)
    if target == native:
        return list(ordered)
    if RANK[target] < RANK[native]:
        raise ValueError(f"cannot turn {native} data into {target}: nothing is up-sampled")
    buckets: dict[date, list[Obs]] = {}
    for p in ordered:
        buckets.setdefault(bucket_start(p.period, target), []).append(p)
    result: list[Obs] = []
    for start, members in sorted(buckets.items()):
        if not _complete(start, members, native, target):
            continue
        values = [m.value for m in members]
        if how == "end":
            value = values[-1]
        elif how == "sum":
            value = sum(values)
        else:
            value = sum(values) / len(values)
        result.append(Obs(start, value))
    return result


def _complete(start: date, members: Sequence[Obs], native: Frequency, target: Frequency) -> bool:
    if native in _MONTHS and target in _MONTHS:
        return len(members) == _MONTHS[target] // _MONTHS[native]
    end = bucket_end(start, target)
    last = max(m.period for m in members)
    first = min(m.period for m in members)
    tail = _TAIL_DAYS[native]
    head = tail if native == "weekly" else 4
    return (end - last).days < tail and (first - start).days <= head


PocUnit = Literal["%", "pp", "as published"]


def _slot(day: date, freq: Frequency) -> int:
    """A number that grows by one per period of `freq`, so a gap shows as a jump."""
    if freq == "daily":
        return day.toordinal()
    if freq == "weekly":
        return day.toordinal() // 7
    months = day.year * 12 + day.month - 1
    return months // {"monthly": 1, "quarterly": 3, "semi_annual": 6, "annual": 12}[freq]


def poc(
    points: Sequence[Obs],
    freq: Frequency,
    *,
    in_points: bool,
    published_as_change: bool = False,
) -> tuple[list[Obs], PocUnit]:
    """The change from the previous display period.

    - published as a change: shown as published, never changed again;
    - a rate or spread (`in_points`): the difference, in percentage points;
    - anything else: the percent change, skipped where the base is zero or negative because a
      percent change on it is not meaningful.
    A missing period is never bridged: the previous point must be the period just before (daily
    series follow the previous business day), otherwise that change is left out.
    """
    ordered = sorted(points, key=lambda p: p.period)
    if published_as_change:
        return list(ordered), "as published"
    out: list[Obs] = []
    for before, now in pairwise(ordered):
        if freq != "daily" and _slot(now.period, freq) - _slot(before.period, freq) != 1:
            continue
        if in_points:
            out.append(Obs(now.period, now.value - before.value))
        elif before.value > 0:
            out.append(Obs(now.period, (now.value / before.value - 1) * 100))
    return out, "pp" if in_points else "%"
