"""Eurostat connector and ingest: JSON-stat parsing, identification, refusal stop, release dates."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date

import httpx
import pytest

from app.connectors.base import USER_AGENT
from app.connectors.eurostat import EurostatClient, EurostatError, parse
from app.data.eurostat_calendar import hicp_release, production_release
from app.data.gap_ids import EUROSTAT_BY_ID, EUROSTAT_SERIES, HISTORY_START
from app.data.macro_catalog import BY_ID
from app.jobs import ingest_eurostat
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def body(values=None, geo_size=1):
    """A JSON-stat message for one series over four months of 2026 (dict values, as Eurostat)."""
    values = values if values is not None else {"0": 100.5, "1": 101.0, "3": 99.0}
    return {
        "label": "Production in industry",
        "id": ["freq", "geo", "time"],
        "size": [1, geo_size, 4],
        "dimension": {
            "time": {
                "category": {"index": {"2026-06": 0, "2026-07": 1, "2026-08": 2, "2026-09": 3}}
            }
        },
        "value": values,
    }


def client_for(handler):
    return EurostatClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_values_are_read_by_month_and_gaps_are_not_filled():
    series = parse(body())
    assert series.observations == [
        (date(2026, 6, 1), 100.5),
        (date(2026, 7, 1), 101.0),
        (date(2026, 9, 1), 99.0),  # August is absent: not interpolated
    ]


def test_a_list_of_values_with_nulls_is_read_too():
    series = parse(body([None, 1.0, 2.0, None]))
    assert [p for p, _ in series.observations] == [date(2026, 7, 1), date(2026, 8, 1)]


def test_more_than_one_series_or_no_data_is_an_error():
    with pytest.raises(EurostatError, match="more than one series"):
        parse(body(geo_size=2))
    with pytest.raises(EurostatError):
        parse({"error": "x"})
    with pytest.raises(EurostatError, match="no observations"):
        parse(body({}))


def test_the_request_names_itself_pins_every_dimension_and_starts_where_asked():
    seen = []

    def handler(request):
        seen.append((request.url.path, dict(request.url.params), request.headers["user-agent"]))
        return httpx.Response(200, json=body())

    spec = EUROSTAT_BY_ID["ESTAT_IP_DE"]
    client_for(handler).series(spec.dataset, spec.filters, date(1990, 1, 1))
    path, params, agent = seen[0]
    assert path.endswith("/data/sts_inpr_m") and agent == USER_AGENT
    assert (
        params["geo"] == "DE"
        and params["s_adj"] == "SCA"
        and params["sinceTimePeriod"] == "1990-01"
    )


def test_a_dataset_or_filter_that_could_change_the_request_is_refused_before_sending():
    calls = []
    client = client_for(lambda r: calls.append(r) or httpx.Response(200, json=body()))
    with pytest.raises(EurostatError):
        client.series("sts_inpr_m/../x", {"geo": "DE"})
    with pytest.raises(EurostatError):
        client.series("sts_inpr_m", {"geo": "DE&geo=FR"})
    assert calls == []


def test_after_a_refusal_the_client_stops_asking_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = client_for(handler)
    with pytest.raises(EurostatError):
        client.series("sts_inpr_m", {"geo": "DE"})
    first = len(calls)
    with pytest.raises(EurostatError, match="not asking again"):
        client.series("sts_inpr_m", {"geo": "DE"})
    assert len(calls) == first


def test_release_dates_err_late():
    assert production_release(date(2026, 9, 1)) == date(2026, 11, 30)  # published 13 November
    assert hicp_release(date(2026, 10, 1)) == date(2026, 11, 30)


def test_the_catalog_declares_the_series_from_1990_with_the_right_change_kind():
    for spec in EUROSTAT_SERIES:
        entry = BY_ID[spec.id]
        assert entry.source == "eurostat" and entry.history_start == HISTORY_START
    assert BY_ID["ESTAT_CORE_DE"].published_as_change  # an annual rate: never changed again
    assert not BY_ID["ESTAT_IP_DE"].published_as_change and BY_ID["ESTAT_IP_DE"].change == "pct"
    assert EUROSTAT_BY_ID["ESTAT_IP_EA21"].country == "EA"


def test_ingest_stores_by_the_release_rule_and_reports_bad_ids(db_session):
    results = ingest_eurostat.ingest(
        client_for(lambda r: httpx.Response(200, json=body())),
        db_session,
        ["ESTAT_IP_DE", "NOT_ESTAT"],
        today=date(2026, 12, 31),
        sleep=lambda _s: None,
    )
    assert results[0].error is None and results[0].rows == 3
    assert results[1].error == "not a Eurostat series in the catalog"
    store = MacroStore(db_session)
    seen = {v.period: v.realtime_start for v in store.as_of("ESTAT_IP_DE", date(2026, 12, 31))}
    assert seen[date(2026, 6, 1)] == date(2026, 8, 31)  # the rule, not the day it was read
    assert store.get_series("ESTAT_IP_DE").seasonal_adjustment == "Seasonally and Calendar Adjusted"


def test_a_failing_series_is_reported_and_rolled_back(db_session):
    results = ingest_eurostat.ingest(
        client_for(lambda r: httpx.Response(200, json={"error": "none"})),
        db_session,
        ["ESTAT_IP_DE"],
        today=date(2026, 12, 31),
    )
    assert results[0].rows is None and "no data" in results[0].error
    assert MacroStore(db_session).list_series() == []
