"""Put one indicator of many countries on a common basis, so they can be ranked side by side.

Countries publish the same indicator in different forms (rule 23): the US consumer price index is
a level (1982-84 = 100) while most other offices, and the IMF, publish its annual rate of change.
Ranking 337 against 3.1 means nothing, so a comparison reads every country as the same quantity:

- consumer prices: the year-on-year change in percent. A series already published as a change is
  used as it is (never changed again, rule 13); an index level becomes (v / v a year ago - 1) x 100;
- unemployment: the rate in percent of the labour force, never a head count, so population size
  drops out.

Only indicators listed in `BASES` can be compared this way; any other must declare its basis first
(`COMPARED_AS`), and the by-indicator view builds on this list as more are added.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Basis:
    label: str  # what the compared number is, e.g. "Year-on-year change"
    unit: str  # "%" or "% of labour force": how a figure is written
    from_level: bool  # an index level is converted to its year-on-year change
    higher_is: str  # "worse" or "better": for ranking and colour, never for a score


BASES: dict[str, Basis] = {
    "consumer_prices": Basis("Year-on-year change", "%", True, "worse"),
    "unemployment_rate": Basis("Share of the labour force", "%", False, "worse"),
}


@dataclass(frozen=True)
class Point:
    period: date
    value: float


def _months(d: date) -> int:
    return d.year * 12 + d.month


def year_on_year(points: Sequence[Point]) -> list[Point]:
    """Percent change against the same month a year earlier; periods without that month drop out."""
    by_month = {_months(p.period): p for p in points}
    result = []
    for p in points:
        before = by_month.get(_months(p.period) - 12)
        if before is not None and before.value != 0:
            result.append(Point(p.period, (p.value / before.value - 1) * 100))
    return result


def on_basis(
    concept: str, points: Sequence[Point], *, published_as_change: bool = False
) -> list[Point]:
    """The series as the comparison reads it: oldest first, nulls already removed."""
    basis = BASES[concept]
    ordered = sorted(points, key=lambda p: p.period)
    if basis.from_level and not published_as_change:
        return year_on_year(ordered)
    return ordered


def points_ago(points: Sequence[Point], months: int) -> Point | None:
    """The point `months` before the latest, if the series has that exact month."""
    if not points:
        return None
    target = _months(points[-1].period) - months
    return next((p for p in reversed(points) if _months(p.period) == target), None)
