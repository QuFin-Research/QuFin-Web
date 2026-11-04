"""Rule 16: the same data stored twice fails the release check, whatever it is called."""

from datetime import UTC, date, datetime, timedelta

from app.domain.duplicates import find_duplicates
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
