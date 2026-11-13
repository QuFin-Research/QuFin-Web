"""World Bank connector and ingest: batches, pagination, identification, refusal stop, dating."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date

import httpx
import pytest

from app.connectors.base import USER_AGENT
from app.connectors.worldbank import (
    MAX_COUNTRIES_PER_REQUEST,
    WorldBankClient,
    WorldBankError,
)
from app.data.macro_catalog import BY_ID
from app.data.worldbank_calendar import annual_release
from app.data.worldbank_ids import HISTORY_START, WB_BY_ID, WB_INDICATORS, WB_SERIES
from app.jobs import ingest_worldbank
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def row(iso3, year, value):
    return {"countryiso3code": iso3, "date": str(year), "value": value}


def message(rows, pages=1, page=1):
    return [{"page": page, "pages": pages, "per_page": 1000, "total": len(rows)}, rows]


def client_for(handler):
    return WorldBankClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_values_are_read_by_country_and_year_and_nulls_are_skipped():
    def handler(request):
        return httpx.Response(
            200,
            json=message(
                [
                    row("ALB", 2023, 3.0),
                    row("ALB", 2022, None),
                    row("AUT", 2023, 1.5),
                    row("XXX", 1, 1),
                ]
            ),
        )

    data = client_for(handler).indicator("NY.GDP.MKTP.KD", ["ALB", "AUT"], date(2020, 1, 1))
    assert data == {"ALB": [(date(2023, 1, 1), 3.0)], "AUT": [(date(2023, 1, 1), 1.5)]}


def test_pages_are_followed_until_the_last():
    pages = {
        "1": message([row("ALB", 2022, 1.0)], pages=2, page=1),
        "2": message([row("ALB", 2023, 2.0)], pages=2, page=2),
    }
    seen = []

    def handler(request):
        seen.append(request.url.params["page"])
        return httpx.Response(200, json=pages[request.url.params["page"]])

    data = client_for(handler).indicator("NY.GDP.MKTP.KD", ["ALB"])
    assert [v for _, v in data["ALB"]] == [1.0, 2.0] and seen == ["1", "2"]


def test_the_request_names_itself_and_joins_the_countries():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers["user-agent"]))
        return httpx.Response(200, json=message([]))

    client_for(handler).indicator("SL.UEM.TOTL.ZS", ["ALB", "AUT"])
    assert seen == [("/v2/country/ALB;AUT/indicator/SL.UEM.TOTL.ZS", USER_AGENT)]


def test_more_than_ten_countries_or_a_bad_code_is_refused_before_sending():
    calls = []
    client = client_for(lambda r: calls.append(r) or httpx.Response(200, json=message([])))
    with pytest.raises(WorldBankError):
        client.indicator("NY.GDP.MKTP.KD", ["AAA"] * (MAX_COUNTRIES_PER_REQUEST + 1))
    with pytest.raises(WorldBankError):
        client.indicator("NY.GDP.MKTP.KD", ["ALB/../x"])
    with pytest.raises(WorldBankError):
        client.indicator("../x", ["ALB"])
    assert calls == []


def test_after_a_refusal_the_client_stops_asking_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = client_for(handler)
    with pytest.raises(WorldBankError):
        client.indicator("NY.GDP.MKTP.KD", ["ALB"])
    first = len(calls)
    with pytest.raises(WorldBankError, match="not asking again"):
        client.indicator("NY.GDP.MKTP.KD", ["ALB"])
    assert len(calls) == first


def test_the_client_is_gentle_by_default():
    assert WorldBankClient.min_interval >= 3.0 and MAX_COUNTRIES_PER_REQUEST <= 10


def test_a_year_is_dated_late_never_early():
    assert annual_release(date(2024, 1, 1)) == date(2025, 12, 31)


def test_every_series_is_in_the_catalog_from_1990_with_a_declared_unit():
    from app.data.series_units import SERIES_UNITS

    assert WB_SERIES and set(WB_BY_ID) == {s.id for s in WB_SERIES}
    for spec in WB_SERIES:
        entry = BY_ID[spec.id]
        assert entry.source == "worldbank" and entry.history_start == HISTORY_START
        assert spec.id in SERIES_UNITS
    assert {i.code for i in WB_INDICATORS} >= {"NY.GDP.MKTP.KD", "SL.UEM.TOTL.ZS"}


def test_ingest_groups_countries_and_dates_each_year_by_the_release_rule(db_session):
    spec = next(s for s in WB_SERIES if s.indicator.code == "NY.GDP.MKTP.KD")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            200, json=message([row(spec.iso3, 2023, 10.0), row(spec.iso3, 2024, 11.0)])
        )

    results = ingest_worldbank.ingest(
        client_for(handler),
        db_session,
        [spec.id, "NOT_WB"],
        today=date(2026, 12, 31),
        sleep=lambda _s: None,
    )
    by_id = {r.series_id: r for r in results}
    assert by_id[spec.id].error is None and by_id[spec.id].rows == 2
    assert by_id["NOT_WB"].error == "not a World Bank series in the catalog"
    assert len(calls) == 1  # one request for the one indicator
    store = MacroStore(db_session)
    seen = {v.period: v.realtime_start for v in store.as_of(spec.id, date(2026, 12, 31))}
    assert seen[date(2023, 1, 1)] == date(2024, 12, 31)
    assert store.get_series(spec.id).frequency == "Annual"


def test_a_country_the_world_bank_has_no_data_for_is_reported_not_stored(db_session):
    spec = WB_SERIES[0]
    results = ingest_worldbank.ingest(
        client_for(lambda r: httpx.Response(200, json=message([]))),
        db_session,
        [spec.id],
        today=date(2026, 12, 31),
    )
    assert results[0].rows is None and "no observations" in results[0].error
    assert MacroStore(db_session).list_series() == []
