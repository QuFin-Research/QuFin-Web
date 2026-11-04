"""Find series that carry the same data, whatever they are called or where they come from.

QuFin rule 16: no duplicated data, at any cost. The catalog test catches two series filed under
the same concept; this catches the case it cannot, a duplicate filed under a different concept
(e.g. the same EIA figure from the EIA API and from FRED under another id, or one series in
thousands and another in millions). Two series are duplicates when, over the periods both
cover, nearly all their values are equal, or nearly all stand in one fixed ratio.
"""

from collections.abc import Mapping
from datetime import date
from itertools import combinations

# Enough shared periods that a match is not chance, and enough distinct values that a flat
# stretch (a policy rate held at zero) does not look like a match.
MIN_SHARED_PERIODS = 20
MIN_DISTINCT_VALUES = 5
# Share of shared periods that must match; below 1 so that one side's late revision does not
# hide a duplicate.
MATCH_SHARE = 0.95
TOLERANCE = 1e-6


def _close(a: float, b: float) -> bool:
    # Relative only: an absolute floor would make every pair of tiny ratios look equal.
    return abs(a - b) <= TOLERANCE * max(abs(a), abs(b)) or a == b


def _relation(a: Mapping[date, float | None], b: Mapping[date, float | None]) -> str | None:
    shared: list[tuple[float, float]] = []
    for period in a.keys() & b.keys():
        x, y = a[period], b[period]
        if x is not None and y is not None:
            shared.append((x, y))
    if len(shared) < MIN_SHARED_PERIODS or len({x for x, _ in shared}) < MIN_DISTINCT_VALUES:
        return None
    needed = MATCH_SHARE * len(shared)
    if sum(_close(x, y) for x, y in shared) >= needed:
        return "the same values"
    ratios = sorted(x / y for x, y in shared if y)
    if not ratios:
        return None
    ratio = ratios[len(ratios) // 2]
    if ratio and sum(_close(r, ratio) for r in ratios) >= needed:
        return f"the same values times {ratio:g} (the same data in other units)"
    return None


def find_duplicates(values: Mapping[str, Mapping[date, float | None]]) -> dict[str, str]:
    """Series id -> why it duplicates another, for every series in a duplicated pair."""
    found: dict[str, list[str]] = {}
    for x, y in combinations(sorted(values), 2):
        if relation := _relation(values[x], values[y]):
            found.setdefault(x, []).append(f"{y} ({relation})")
            found.setdefault(y, []).append(f"{x} ({relation})")
    return {
        series_id: "Duplicated data: matches " + "; ".join(others) + ". Keep one series (rule 16)"
        for series_id, others in found.items()
    }
