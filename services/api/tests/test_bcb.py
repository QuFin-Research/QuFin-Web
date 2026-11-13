"""Banco Central do Brasil SGS connector and ingest: windows, parsing, refusal stop, dating."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date
from itertools import pairwise

import httpx
import pytest

from app.connectors.base import USER_AGENT
from app.connectors.bcb import BcbClient, BcbError, windows
from app.data.gap_ids import BCB_BY_ID, BCB_SERIES, HISTORY_START
from app.data.macro_catalog import BY_ID
from app.data.national_calendar import brazil_release
from app.jobs import ingest_national
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def client_for(handler):
    return BcbClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def rows(*pairs):
    return [{"data": d, "valor": v} for d, v in pairs]


def test_a_long_history_is_asked_for_in_windows_of_at_most_ten_years():
    spans = windows(date(1990, 1, 1), date(2026, 11, 13))
    assert spans[0][0] == date(1990, 1, 1) and spans[-1][1] == date(2026, 11, 13)
    assert all((b - a).days <= 3660 for a, b in spans) and len(spans) == 4
    for (_, end), (start, _) in pairwise(spans):
        assert (start - end).days == 1  # no gap and no overlap between windows
    assert windows(date(2023, 1, 1), date(2026, 11, 13)) == [(date(2023, 1, 1), date(2026, 11, 13))]


def test_values_are_read_and_blank_values_skipped_and_windows_merged():
    seen = []

    def handler(request):
        seen.append((request.url.path, dict(request.url.params), request.headers["user-agent"]))
        if request.url.params["dataInicial"].endswith("2005"):
            return httpx.Response(200, json=rows(("01/02/2005", "7.5"), ("01/03/2005", "")))
        return httpx.Response(200, json=rows(("01/01/1995", "6.1")))

    data = client_for(handler).series(24369, date(1995, 1, 1), date(2005, 6, 30))
    assert data == [(date(1995, 1, 1), 6.1), (date(2005, 2, 1), 7.5)]
    path, params, agent = seen[0]
    assert path == "/dados/serie/bcdata.sgs.24369/dados" and agent == USER_AGENT
    assert params["formato"] == "json" and params["dataInicial"] == "01/01/1995"


def test_no_observations_or_a_bad_message_or_code_is_an_error():
    with pytest.raises(BcbError, match="no observations"):
        client_for(lambda r: httpx.Response(200, json=[])).series(
            1, date(2025, 1, 1), date(2025, 6, 1)
        )
    with pytest.raises(BcbError, match="unexpected"):
        client_for(lambda r: httpx.Response(200, json={"error": 1})).series(
            1, date(2025, 1, 1), date(2025, 6, 1)
        )
    with pytest.raises(BcbError):
        client_for(lambda r: httpx.Response(200, json=[])).series(0, date(2025, 1, 1))


def test_after_a_refusal_the_client_stops_asking_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = client_for(handler)
    with pytest.raises(BcbError):
        client.series(24369, date(2025, 1, 1), date(2025, 6, 1))
    first = len(calls)
    with pytest.raises(BcbError, match="not asking again"):
        client.series(24369, date(2025, 1, 1), date(2025, 6, 1))
    assert len(calls) == first


def test_release_is_dated_the_last_weekday_of_the_following_month():
    assert brazil_release(date(2026, 9, 1)) == date(2026, 10, 30)


def test_the_catalog_has_both_series_from_1990_on_the_right_concepts():
    assert {s.code for s in BCB_SERIES} == {24369, 22707}
    for spec in BCB_SERIES:
        entry = BY_ID[spec.id]
        assert (
            entry.source == "bcb" and entry.country == "BR" and entry.history_start == HISTORY_START
        )
    assert BCB_BY_ID["BCB_24369"].concept == "unemployment_rate"
    assert BCB_BY_ID["BCB_22707"].concept == "merchandise_trade_balance"


def test_ingest_dates_each_month_by_the_rule_and_reports_bad_ids(db_session):
    results = ingest_national.ingest_bcb(
        client_for(
            lambda r: httpx.Response(200, json=rows(("01/08/2026", "5.6"), ("01/09/2026", "5.2")))
        ),
        db_session,
        ["BCB_24369", "NOT_BCB"],
        today=date(2026, 11, 13),
        sleep=lambda _s: None,
    )
    by_id = {r.series_id: r for r in results}
    assert by_id["BCB_24369"].error is None and by_id["BCB_24369"].rows == 2
    assert by_id["NOT_BCB"].error == "not a BCB series in the catalog"
    store = MacroStore(db_session)
    seen = {v.period: v.realtime_start for v in store.as_of("BCB_24369", date(2026, 11, 13))}
    assert seen[date(2026, 9, 1)] == date(2026, 10, 30)
    assert store.get_series("BCB_24369").seasonal_adjustment == "Not Seasonally Adjusted"


def test_a_failing_series_is_reported_and_rolled_back(db_session):
    results = ingest_national.ingest_bcb(
        client_for(lambda r: httpx.Response(200, json=[])),
        db_session,
        ["BCB_22707"],
        today=date(2026, 11, 13),
    )
    assert results[0].rows is None and "no observations" in results[0].error
    assert MacroStore(db_session).list_series() == []


def test_a_window_before_the_series_began_is_empty_but_other_errors_still_stop_the_load():
    def handler(request):
        if request.url.params["dataInicial"].endswith("1990"):
            return httpx.Response(
                404, json={"erro": {"statusCode": 404, "detail": "Value(s) not found"}}
            )
        return httpx.Response(200, json=rows(("01/05/2012", "7.7")))

    data = client_for(handler).series(24369, date(1990, 1, 1), date(2012, 12, 31))
    assert data == [(date(2012, 5, 1), 7.7)]
    with pytest.raises(BcbError, match="returned 500"):
        client_for(lambda r: httpx.Response(500, text="boom")).series(
            24369, date(2020, 1, 1), date(2021, 1, 1)
        )
