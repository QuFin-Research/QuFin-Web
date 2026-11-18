"""Find series that carry the same data, whatever they are called or where they come from.

QuFin rule 16: no duplicated data, at any cost. The catalog test catches two series filed under
the same concept; this catches the case it cannot, a duplicate filed under a different concept
(e.g. the same EIA figure from the EIA API and from FRED under another id, or one series in
thousands and another in millions). Two series are duplicates when, over the periods both
cover, nearly all their values are equal, or nearly all stand in one fixed ratio.

Comparing every series with every other grows with the square of the series count, so a cheap
pre-filter picks the pairs that need the full comparison (`_relation`); it never decides a
duplicate itself. It works from an index of fingerprints:

- *Shape keys* (any unit): for two consecutive periods p and q of a series, the ratio of its two
  values. A change of unit multiplies both values, so the ratio, and therefore the key, is the
  same for the same data in any unit. Two series that share a few of these keys are candidates.
- *Value keys* (same unit): a period and the value in it, for series on different period grids
  (a daily series and a monthly one that repeats its month-end value).

A series with too few usable keys (mostly zero or empty values) is compared with every other
series, so the filter cannot hide a duplicate. Tests check that it finds every pair the full
comparison finds.
"""

import math
import time
from collections import defaultdict
from collections.abc import Collection, Mapping
from datetime import date
from itertools import combinations, pairwise

# Enough shared periods that a match is not chance, and enough distinct values that a flat
# stretch (a policy rate held at zero) does not look like a match.
MIN_SHARED_PERIODS = 20
MIN_DISTINCT_VALUES = 5
# Share of shared periods that must match; below 1 so that one side's late revision does not
# hide a duplicate.
MATCH_SHARE = 0.95
TOLERANCE = 1e-6

# Pre-filter. Buckets are far wider than TOLERANCE, so a match is always in the same or an
# adjacent bucket.
BUCKET_WIDTH = 1e-4
MIN_SHARED_SHAPES = 3
MIN_SHARED_VALUES = int(MIN_SHARED_PERIODS * MATCH_SHARE)
# A series needs this share of its consecutive pairs usable as shape keys, else it is compared
# with every other series.
MIN_KEYABLE_SHARE = 0.6

Values = Mapping[date, float | None]
Pair = frozenset[str]


class DuplicateCheckTimeoutError(RuntimeError):
    """The check ran out of its time budget. It fails; it is never skipped (rule 16)."""


def _close(a: float, b: float) -> bool:
    # Relative only: an absolute floor would make every pair of tiny ratios look equal.
    return abs(a - b) <= TOLERANCE * max(abs(a), abs(b)) or a == b


def _relation(a: Values, b: Values) -> str | None:
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


def _bucket(x: float) -> tuple[int, int]:
    """Sign and bucket of log|x|, for a non-zero x."""
    return (1 if x > 0 else -1, math.floor(math.log(abs(x)) / BUCKET_WIDTH))


def _observed(series: Values) -> list[tuple[date, float]]:
    return sorted((p, v) for p, v in series.items() if v is not None)


def _shape_keys(points: list[tuple[date, float]]) -> tuple[set[tuple], int]:
    """Keys of consecutive pairs, and how many pairs there were."""
    keys: set[tuple] = set()
    for (p, x), (q, y) in pairwise(points):
        if x and y:
            ratio_sign, b = _bucket(x / y)
            keys.add((p, q, ratio_sign, b))
    return keys, max(len(points) - 1, 0)


def candidate_pairs(values: Mapping[str, Values]) -> set[Pair]:
    """The pairs worth a full comparison: every pair `_relation` could match is among them."""
    points = {sid: _observed(series) for sid, series in values.items()}
    usable = {
        sid: pts
        for sid, pts in points.items()
        if len(pts) >= MIN_SHARED_PERIODS and len({v for _, v in pts}) >= MIN_DISTINCT_VALUES - 1
    }
    shape_index: dict[tuple, list[str]] = defaultdict(list)
    value_index: dict[tuple, list[str]] = defaultdict(list)
    everywhere: set[str] = set()
    for sid, pts in usable.items():
        keys, pairs = _shape_keys(pts)
        if not pairs or len(keys) < MIN_KEYABLE_SHARE * pairs:
            everywhere.add(sid)
        for key in keys:
            shape_index[key].append(sid)
        for p, v in pts:
            if v:
                value_index[(p, *_bucket(v))].append(sid)

    shapes: dict[Pair, int] = defaultdict(int)
    for members in shape_index.values():
        for a, b in combinations(members, 2):
            shapes[frozenset((a, b))] += 1
    same_values: dict[Pair, int] = defaultdict(int)
    for (p, sign, b), members in value_index.items():
        for x, y in combinations(members, 2):
            same_values[frozenset((x, y))] += 1
        # A value near a bucket edge lands in the next bucket: count those pairs from the lower one.
        for y in value_index.get((p, sign, b + 1), ()):
            for x in members:
                same_values[frozenset((x, y))] += 1

    found = {pair for pair, n in shapes.items() if n >= MIN_SHARED_SHAPES}
    found |= {pair for pair, n in same_values.items() if n >= MIN_SHARED_VALUES}
    for sid in everywhere:
        found |= {frozenset((sid, other)) for other in usable if other != sid}
    return found


def find_duplicates(
    values: Mapping[str, Values],
    *,
    exempt: Collection[Pair] = (),
    budget_seconds: float | None = None,
) -> dict[str, str]:
    """Series id -> why it duplicates another, for every series in a duplicated pair.

    `exempt` lists pairs that are expected to match and are not reported: a retired series and
    the later series of its own pair (rule 16). Everything else is compared. When
    `budget_seconds` runs out the check raises `DuplicateCheckTimeoutError`; it never returns a
    partial answer.
    """
    skip = set(exempt)
    start = time.monotonic()
    found: dict[str, list[str]] = {}
    for n, pair in enumerate(sorted(tuple(sorted(p)) for p in candidate_pairs(values))):
        if (
            budget_seconds is not None
            and n % 256 == 0
            and time.monotonic() - start > budget_seconds
        ):
            raise DuplicateCheckTimeoutError(
                f"the duplicate check took longer than {budget_seconds}s"
            )
        x, y = pair
        if frozenset(pair) in skip:
            continue
        if relation := _relation(values[x], values[y]):
            found.setdefault(x, []).append(f"{y} ({relation})")
            found.setdefault(y, []).append(f"{x} ({relation})")
    return {
        series_id: "Duplicated data: matches "
        + "; ".join(sorted(others))
        + ". Keep one series (rule 16)"
        for series_id, others in found.items()
    }
