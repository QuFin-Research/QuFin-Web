"""Rule 16: the same data stored twice fails the release check, whatever it is called."""

import random
from datetime import UTC, date, datetime, timedelta
from itertools import combinations

import pytest

from app.domain.duplicates import (
    DuplicateCheckTimeoutError,
    _relation,
    candidate_pairs,
    find_duplicates,
)
from app.jobs.check_data import check_macro
from app.stores.macro import MacroStore, SeriesMeta
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

WEEKS = [date(2024, 1, 5) + timedelta(weeks=i) for i in range(60)]
CRUDE = {d: 400_000.0 + 1_000 * (i % 13) - 37 * i for i, d in enumerate(WEEKS)}


def test_identical_values_under_another_id_are_duplicates():
    found = find_duplicates({"A": CRUDE, "B": dict(CRUDE)})
    assert set(found) == {"A", "B"}
    assert "B (the same values)" in found["A"]


def test_same_data_in_other_units_is_a_duplicate():
    millions = {d: v / 1000 for d, v in CRUDE.items()}
    found = find_duplicates({"THOUSANDS": CRUDE, "MILLIONS": millions})
    assert "the same data in other units" in found["MILLIONS"]


def test_a_late_revision_on_one_side_does_not_hide_a_duplicate():
    revised = dict(CRUDE)
    revised[WEEKS[-1]] += 250
    assert set(find_duplicates({"A": CRUDE, "B": revised})) == {"A", "B"}


def test_different_or_flat_or_short_series_are_not_duplicates():
    other = {d: v + (i % 7) * 900 for i, (d, v) in enumerate(CRUDE.items())}
    flat = {d: 0.25 for d in WEEKS}
    short = {d: CRUDE[d] for d in WEEKS[:10]}
    assert find_duplicates({"A": CRUDE, "B": other}) == {}
    assert find_duplicates({"RATE1": flat, "RATE2": dict(flat)}) == {}  # zero-rate stretch
    assert find_duplicates({"A": CRUDE, "SHORT": short}) == {}


def test_unrelated_series_of_very_different_size_are_not_duplicates():
    # Ratios of a small rate to a huge stock are all tiny; tiny is not the same as constant.
    rate = {d: 1.0 + 0.1 * (i % 9) for i, d in enumerate(WEEKS)}
    credit = {d: 5_000_000.0 + 3_000 * i for i, d in enumerate(WEEKS)}
    assert find_duplicates({"RATE": rate, "CREDIT": credit}) == {}


def _brute_force(values):
    """Every pair compared, as the check did before the pre-filter."""
    found = set()
    for x, y in combinations(sorted(values), 2):
        if _relation(values[x], values[y]):
            found.add(frozenset((x, y)))
    return found


def _random_universe(seed):
    rng = random.Random(seed)  # noqa: S311  (reproducible test data)
    base = []
    for _ in range(14):
        level, step = rng.uniform(1, 1e6), rng.uniform(0.001, 0.05)
        walk = []
        for _ in range(60):
            level *= 1 + rng.uniform(-step, step)
            walk.append(level)
        base.append(walk)
    series = {}
    for i, walk in enumerate(base):
        series[f"S{i}"] = dict(zip(WEEKS, walk, strict=True))
    for i in range(0, 14, 2):  # duplicates: same, other units, a revision, a gap, a negative
        walk = base[i]
        series[f"D{i}a"] = {d: v for d, v in zip(WEEKS, walk, strict=True)}
        series[f"D{i}b"] = {
            d: v * rng.choice([1000, 0.001, 12.5]) for d, v in zip(WEEKS, walk, strict=True)
        }
    series["REV"] = {**series["D0a"], WEEKS[3]: series["D0a"][WEEKS[3]] * 1.2}
    series["GAPS"] = {d: v for k, (d, v) in enumerate(series["D2a"].items()) if k % 11 != 0}
    series["NEG"] = {d: -v for d, v in series["S4"].items()}
    series["ZEROS"] = {d: (0.0 if k % 2 else v) for k, (d, v) in enumerate(series["S6"].items())}
    series["ZEROS2"] = dict(series["ZEROS"])
    # a daily-style series that repeats the weekly values on the shared dates only
    extra = {d + timedelta(days=1): 1.0 + k for k, d in enumerate(WEEKS)}
    series["MIXED"] = {**series["S8"], **extra}
    return series


def test_the_prefilter_finds_every_pair_the_full_comparison_finds():
    for seed in range(5):
        series = _random_universe(seed)
        full = _brute_force(series)
        assert full, "the universe must hold duplicates"
        assert full <= candidate_pairs(series)
        assert set(find_duplicates(series)) == {sid for pair in full for sid in pair}


def test_the_prefilter_does_not_compare_every_pair():
    series = {}
    rng = random.Random(1)  # noqa: S311  (reproducible test data)
    for i in range(200):
        level, walk = rng.uniform(1, 1e5), []
        for _ in range(60):
            level *= 1 + rng.uniform(-0.03, 0.03)
            walk.append(level)
        series[f"X{i}"] = dict(zip(WEEKS, walk, strict=True))
    series["X0COPY"] = {d: v / 1000 for d, v in series["X0"].items()}
    pairs = candidate_pairs(series)
    assert frozenset(("X0", "X0COPY")) in pairs
    assert len(pairs) < 100  # 201 series have 20,100 pairs


def test_exempt_pairs_are_not_reported_but_other_pairs_still_are():
    series = {"OLD": CRUDE, "NEW": dict(CRUDE), "OTHER": dict(CRUDE)}
    found = find_duplicates(series, exempt={frozenset(("OLD", "NEW"))})
    assert "NEW (the same values)" not in found["OLD"]
    assert "OTHER (the same values)" in found["OLD"]
    assert "OTHER (the same values)" in found["NEW"]


def test_a_check_out_of_time_fails_it_is_not_skipped():
    series = {"A": CRUDE, "B": dict(CRUDE)}
    with pytest.raises(DuplicateCheckTimeoutError):
        find_duplicates(series, budget_seconds=-1)


def _store(store, series_id, values):
    meta = SeriesMeta(
        series_id,
        "eia",
        series_id,
        "Thousand Barrels",
        "Weekly",
        "NSA",
        "US",
        "energy",
        datetime(2025, 3, 1, tzinfo=UTC),
    )
    store.record_latest(
        meta, sorted(values.items()), lambda d: d + timedelta(days=5), date(2025, 3, 3)
    )


def test_release_check_fails_both_sides_of_a_duplicate(db_session):  # noqa: F811
    store = MacroStore(db_session)
    _store(store, "WCESTUS1", CRUDE)
    _store(store, "WCSSTUS1", {d: v / 1000 for d, v in CRUDE.items()})
    checks = {c.id: c.status.freshness for c in check_macro(db_session, date(2025, 3, 3))}
    for series_id, other in (("WCESTUS1", "WCSSTUS1"), ("WCSSTUS1", "WCESTUS1")):
        assert checks[series_id].status == "review"
        assert not checks[series_id].usable
        assert other in checks[series_id].reason
    assert checks["UNRATE"].reason != checks["WCESTUS1"].reason
