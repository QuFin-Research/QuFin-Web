"""record_latest: stores a source's current values and turns revisions into vintages."""

from datetime import date

from app.stores.macro import OPEN_END, MacroStore, SeriesMeta
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

META = SeriesMeta(
    id="TEST_LATEST",
    source="bls",
    title="Test",
    units="Index",
    frequency="Monthly",
    seasonal_adjustment="Not Seasonally Adjusted",
    country="US",
    dimension="external",
    last_updated=None,
    cycle=None,
    source_name="Test publisher",
    release_name="Test release",
)
PERIOD = date(2026, 10, 1)
TODAY = date(2026, 11, 12)


def rows(store: MacroStore):
    return [(v.realtime_start, v.realtime_end, v.value) for v in store.as_of("TEST_LATEST", TODAY)]


def test_new_period_is_dated_by_its_release_never_after_today(db_session):  # noqa: F811
    store = MacroStore(db_session)
    store.record_latest(META, [(PERIOD, 1.0)], lambda p: date(2026, 12, 15), TODAY)
    assert rows(store) == [(TODAY, OPEN_END, 1.0)]


def test_revision_on_a_later_day_becomes_a_new_vintage(db_session):  # noqa: F811
    store = MacroStore(db_session)
    store.record_latest(META, [(PERIOD, 1.0)], lambda p: date(2026, 11, 5), TODAY)
    store.record_latest(META, [(PERIOD, 2.0)], lambda p: date(2026, 11, 5), date(2026, 11, 20))
    assert store.as_of("TEST_LATEST", date(2026, 11, 10))[0].value == 1.0
    assert store.as_of("TEST_LATEST", date(2026, 11, 20))[0].value == 2.0


def test_revision_on_the_day_a_period_was_first_seen_does_not_repeat_the_key(db_session):  # noqa: F811
    """A second run on the same day (flash then final HICP) corrects the value in place."""
    store = MacroStore(db_session)
    store.record_latest(META, [(PERIOD, 1.0)], lambda p: TODAY, TODAY)
    written = store.record_latest(META, [(PERIOD, 2.0)], lambda p: TODAY, TODAY)
    assert written == 1
    assert rows(store) == [(TODAY, OPEN_END, 2.0)]
