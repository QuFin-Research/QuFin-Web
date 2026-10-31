"""Release-schedule and timeliness rules: stale, discontinued or delayed data is flagged."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.clock import today
from app.domain.freshness import assess, timeliness
from app.jobs.check_data import check_macro, macro_status
from app.stores.macro import SeriesMeta
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)
from tests.test_positioning import TUESDAY
from tests.test_positioning import db_session as _positioning_db  # noqa: F401
from tests.test_positioning import ingested as positioning_ingested  # noqa: F401


def meta(series_id="UNRATE", title="Unemployment Rate", frequency="Monthly", notice=None):
    return SeriesMeta(
        id=series_id,
        source="fred",
        title=title,
        units="Percent",
        frequency=frequency,
        seasonal_adjustment="SA",
        country="US",
        dimension="labour",
        last_updated=datetime(2026, 10, 3, tzinfo=UTC),
        delay_notice=notice,
    )


def monthly_releases(lag_days, months=12, last=date(2026, 9, 1)):
    periods = []
    y, m = last.year, last.month
    for _ in range(months):
        periods.append(date(y, m, 1))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return {p: p + timedelta(days=lag_days) for p in periods}


# --- schedule ------------------------------------------------------------------------------


def test_on_schedule_until_the_next_release_is_overdue():
    common = dict(title="X", frequency="Monthly", last_period=date(2026, 9, 1), release_lags=[33])
    # due = Sep 1 + 31 + 33 days = Nov 4; 14 days of grace for a monthly series
    ok = assess(**common, today=date(2026, 11, 18))
    assert (ok.status, ok.next_due, ok.usable) == ("ok", date(2026, 11, 4), True)
    late = assess(**common, today=date(2026, 11, 19))
    assert (late.status, late.days_overdue, late.usable) == ("overdue", 15, False)


def test_daily_series_get_a_short_grace():
    common = dict(title="X", frequency="Daily", release_lags=[1], today=date(2026, 11, 10))
    assert assess(**common, last_period=date(2026, 11, 3)).usable
    assert not assess(**common, last_period=date(2026, 11, 2)).usable


def test_discontinued_series_fail_whatever_the_dates():
    f = assess(
        title="Leading Index for the United States (DISCONTINUED)",
        frequency="Monthly",
        last_period=date(2026, 9, 1),
        release_lags=[30],
        today=date(2026, 9, 2),
    )
    assert (f.status, f.usable) == ("discontinued", False)


def test_unknown_frequencies_are_refused():
    with pytest.raises(ValueError):
        assess(
            title="X",
            frequency="Hourly",
            last_period=date(2026, 1, 1),
            release_lags=[],
            today=date(2026, 1, 2),
        )


# --- FRED delays and timeliness -------------------------------------------------------------


def test_delay_notice_without_a_declared_delay_needs_review():
    notice = "At the request of the source, the data is delayed by 1 month."
    status = macro_status(
        meta(notice=notice), date(2026, 9, 1), monthly_releases(26), date(2026, 10, 1)
    )
    assert status.freshness.status == "review"
    assert notice in status.freshness.reason
    assert status.timeliness.weight == 0.0


def test_declared_delay_that_fred_no_longer_reports_needs_review():
    status = macro_status(
        meta("UMCSENT", "University of Michigan: Consumer Sentiment"),
        date(2026, 9, 1),
        monthly_releases(25),
        date(2026, 10, 1),
    )
    assert status.freshness.status == "review"


def test_licensing_delay_moves_the_due_date_and_lowers_the_weight():
    notice = "At the request of the source, the data is delayed by 1 month."
    status = macro_status(
        meta("UMCSENT", "University of Michigan: Consumer Sentiment", notice=notice),
        date(2026, 9, 1),
        monthly_releases(25),
        date(2026, 11, 1),
    )
    assert status.freshness.usable
    assert status.freshness.next_due == date(2026, 9, 1) + timedelta(days=31 + 25 + 30)
    assert status.latest_source_release == date(2026, 9, 26)
    assert status.latest_fred_release == date(2026, 10, 26)
    assert status.timeliness.fred_delay_days == 30
    assert status.timeliness.weight < 1.0


def test_fresh_data_keeps_full_weight_and_late_data_loses_it():
    assert timeliness("Daily", [1], 0, usable=True).weight == 1.0
    assert timeliness("Weekly, Ending Saturday", [5], 0, usable=True).weight == 1.0
    # two months to publish a monthly series: 33 days after the month ends
    assert timeliness("Monthly", [64], 0, usable=True).weight == 0.68
    # 60 more days of delay halves it again
    assert timeliness("Monthly", [64], 60, usable=True).weight == 0.34
    assert timeliness("Daily", [1], 0, usable=False).weight == 0.0


# --- whole-store check and the API ---------------------------------------------------------


def test_catalog_series_that_were_never_ingested_count_as_overdue(ingested, db_session):  # noqa: F811
    checks = {c.id: c for c in check_macro(db_session, date(2026, 10, 10))}
    assert checks["UNRATE"].status.freshness.usable
    assert checks["GDPC1"].status.freshness.reason == "Not ingested"
    assert not checks["GDPC1"].status.freshness.usable


def test_api_reports_source_release_dates_and_status(app, client, ingested):  # noqa: F811
    app.dependency_overrides[today] = lambda: date(2026, 11, 10)
    [s] = client.get("/v1/macro/series").json()
    assert s["sourceName"] == "U.S. Bureau of Labor Statistics"
    assert s["releaseName"] == "Employment Situation"
    assert s["freshness"]["status"] == "ok"
    assert s["timeliness"]["latestSourceRelease"] == "2026-10-03"
    assert s["timeliness"]["latestFredRelease"] == "2026-10-03"
    assert s["timeliness"]["weight"] == 0.98  # released ~2 days after the month ends

    app.dependency_overrides[today] = lambda: date(2026, 12, 1)
    body = client.get("/v1/macro/series/UNRATE").json()
    assert body["freshness"]["status"] == "overdue"
    assert body["freshness"]["usable"] is False
    assert body["timeliness"]["weight"] == 0.0


def test_positioning_reports_overdue_weekly_reports(app, client, positioning_ingested):  # noqa: F811
    latest = TUESDAY + timedelta(weeks=39)
    app.dependency_overrides[today] = lambda: latest + timedelta(days=10)
    [gold] = client.get("/v1/positioning").json()
    assert gold["freshness"]["usable"] is True
    app.dependency_overrides[today] = lambda: latest + timedelta(days=30)
    [gold] = client.get("/v1/positioning").json()
    assert gold["freshness"]["status"] == "overdue"
    # As of a past date, the report schedule is judged at that date.
    past = client.get("/v1/positioning", params={"asOf": (latest + timedelta(days=4)).isoformat()})
    assert past.json()[0]["freshness"]["usable"] is True
