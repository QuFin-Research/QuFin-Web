"""UK ONS connector and ingest: parsing, identification, refusal stop, release dates, catalog."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date

import httpx
import pytest

from app.connectors.base import USER_AGENT
from app.connectors.ons import OnsClient, OnsError, parse_period
from app.data.gap_ids import HISTORY_START, ONS_BY_ID, ONS_SERIES
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, start_for
from app.data.ons_calendar import (
    inflation_release,
    labour_market_release,
    national_accounts_release,
)
from app.jobs import ingest_ons
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

PATH = ONS_BY_ID["ONS_MGSX"].path


def body(key="months", rows=None):
    rows = (
        rows
        if rows is not None
        else [
            {"date": "2026 MAY", "value": "4.6"},
            {"date": "2026 JUN", "value": "4.7"},
            {"date": "1990 JAN", "value": "6.9"},
            {"date": "2026 JUL", "value": ""},  # unpublished
        ]
    )
    return {
        "description": {"title": "t", "unit": "%", "nextRelease": "17 November 2026"},
        key: rows,
    }


def client_for(handler):
    return OnsClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_periods_are_read_as_their_first_day():
    assert parse_period("2026 JUL") == date(2026, 7, 1)
    assert parse_period("2026 Q2") == date(2026, 4, 1)
    with pytest.raises(OnsError):
        parse_period("2026")


def test_series_is_sorted_filtered_by_start_and_skips_blank_values():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers["user-agent"]))
        return httpx.Response(200, json=body())

    data = client_for(handler).series(PATH, "Monthly", date(2000, 1, 1))
    assert data.observations == [(date(2026, 5, 1), 4.6), (date(2026, 6, 1), 4.7)]
    assert data.next_release == "17 November 2026"
    assert seen == [(f"/{PATH}/data", USER_AGENT)]  # identifies itself; asks for one series
    assert "github.com/QuFin-Research" in USER_AGENT
    deep = client_for(lambda r: httpx.Response(200, json=body())).series(PATH, "Monthly", None)
    assert deep.observations[0] == (date(1990, 1, 1), 6.9)


def test_quarterly_series_reads_quarters():
    rows = [{"date": "2026 Q1", "value": "100"}, {"date": "2026 Q2", "value": "101"}]
    data = client_for(lambda r: httpx.Response(200, json=body("quarters", rows))).series(
        "economy/x/timeseries/abmi/qna", "Quarterly"
    )
    assert [p for p, _ in data.observations] == [date(2026, 1, 1), date(2026, 4, 1)]


def test_a_path_that_is_not_a_time_series_page_is_refused_before_any_request():
    calls = []
    client = client_for(lambda r: calls.append(r) or httpx.Response(200, json=body()))
    with pytest.raises(OnsError):
        client.series("../../etc/passwd?x=1", "Monthly")
    assert calls == []


def test_no_months_is_an_error_not_an_empty_series():
    with pytest.raises(OnsError):
        client_for(lambda r: httpx.Response(200, json=body("quarters"))).series(PATH, "Monthly")


def test_after_a_refusal_the_client_stops_asking_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = client_for(handler)
    with pytest.raises(OnsError):
        client.series(PATH, "Monthly")
    first = len(calls)
    with pytest.raises(OnsError, match="not asking again"):
        client.series(PATH, "Monthly")
    assert len(calls) == first  # nothing more was sent


def test_requests_are_paced_to_the_stated_interval():
    waits = []
    client = OnsClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body())),
        sleep=waits.append,
    )
    client.series(PATH, "Monthly")
    client.series(PATH, "Monthly")
    assert OnsClient.min_interval >= 2.0 and waits and waits[0] <= OnsClient.min_interval


def test_release_dates_err_late():
    # The ONS published May-July labour data in mid-September; dated 30 September at the latest.
    assert labour_market_release(date(2026, 7, 1)) == date(2026, 9, 30)
    assert inflation_release(date(2026, 9, 1)) == date(2026, 10, 30)
    assert national_accounts_release(date(2026, 4, 1)) == date(2026, 9, 30)


def test_catalog_declares_the_ons_series_with_the_deep_start():
    for spec in ONS_SERIES:
        entry = BY_ID[spec.id]
        assert entry.source == "ons" and entry.country == "GB"
        assert entry.history_start == HISTORY_START
    assert BY_ID["ONS_DKO8"].published_as_change  # a rate: never changed again (rule 13)
    assert start_for("ONS_MGSX", DEFAULT_OBSERVATION_START) == date(1990, 1, 1)
    assert start_for("ONS_MGSX", date(2015, 1, 1)) == date(2015, 1, 1)  # an explicit start wins
    assert start_for("UNRATE", DEFAULT_OBSERVATION_START) == DEFAULT_OBSERVATION_START


def test_ingest_stores_from_1990_dated_by_release_and_reports_bad_ids(db_session):
    def handler(request):
        return httpx.Response(200, json=body())

    results = ingest_ons.ingest(
        client_for(handler),
        db_session,
        ["ONS_MGSX", "NOT_ONS"],
        today=date(2026, 12, 31),
        sleep=lambda _s: None,
    )
    assert results[0].error is None and results[0].rows == 3
    assert results[1].error == "not an ONS series in the catalog"
    store = MacroStore(db_session)
    seen = {v.period: v.realtime_start for v in store.as_of("ONS_MGSX", date(2026, 12, 31))}
    assert seen[date(1990, 1, 1)] == date(1990, 3, 30)
    assert seen[date(2026, 6, 1)] == date(2026, 8, 31)  # the release rule, not the day it was read
    assert store.get_series("ONS_MGSX").seasonal_adjustment == "Seasonally Adjusted"


def test_one_failing_series_is_reported_and_rolled_back(db_session):
    results = ingest_ons.ingest(
        client_for(lambda r: httpx.Response(200, json=body("quarters"))),
        db_session,
        ["ONS_MGSX"],
        today=date(2026, 12, 31),
    )
    assert results[0].rows is None and "no months" in results[0].error
    assert MacroStore(db_session).list_series() == []
