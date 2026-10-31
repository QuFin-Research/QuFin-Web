"""CFTC connector, COT metrics and the /v1/positioning endpoints."""

from datetime import date, timedelta

import httpx
import pytest

from app.connectors.cftc import CftcClient, CftcError, parse_report
from app.data.positioning_catalog import BY_SYMBOL
from app.domain.positioning import series
from app.jobs import ingest_cftc
from app.stores.db import get_session
from app.stores.positioning import CotReport

TUESDAY = date(2026, 1, 6)


def row(code, report_date, long, short, oi=100_000):
    return {
        "cftc_contract_market_code": code,
        "report_date_as_yyyy_mm_dd": f"{report_date.isoformat()}T00:00:00.000",
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "open_interest_all": str(oi),
        "noncomm_positions_long_all": str(long),
        "noncomm_positions_short_all": str(short),
        "noncomm_postions_spread_all": "1000",
        "comm_positions_long_all": "1",
        "comm_positions_short_all": "2",
        "nonrept_positions_long_all": "3",
        "nonrept_positions_short_all": "4",
    }


def weekly_rows(code, nets, start=TUESDAY):
    return [row(code, start + timedelta(weeks=i), 50_000 + n, 50_000) for i, n in enumerate(nets)]


def report(code, i, net, oi=100_000):
    d = TUESDAY + timedelta(weeks=i)
    return CotReport(code, d, d + timedelta(days=3), "M", oi, 50_000 + net, 50_000, 0, 0, 0, 0, 0)


# --- connector -----------------------------------------------------------------------------


def test_parse_report_sets_the_friday_release_date():
    r = parse_report(row("088691", TUESDAY, 223_724, 37_273, oi=396_810))
    assert r.report_date == TUESDAY
    assert r.release_date == date(2026, 1, 9)  # Friday
    assert (r.noncomm_long, r.noncomm_short, r.open_interest) == (223_724, 37_273, 396_810)


def test_client_pages_and_filters_by_contract():
    rows = weekly_rows("088691", range(7))
    calls = []

    def handler(request: httpx.Request):
        params = request.url.params
        calls.append(int(params["$offset"]))
        assert "cftc_contract_market_code='088691'" in params["$where"]
        assert "report_date_as_yyyy_mm_dd >= '2026-01-01'" in params["$where"]
        offset = int(params["$offset"])
        return httpx.Response(200, json=rows[offset : offset + int(params["$limit"])])

    from app.connectors import cftc

    original = cftc.PAGE_LIMIT
    cftc.PAGE_LIMIT = 3
    try:
        client = CftcClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)
        reports = client.reports("088691", date(2026, 1, 1))
    finally:
        cftc.PAGE_LIMIT = original
    assert calls == [0, 3, 6]
    assert len(reports) == 7


def test_client_rejects_codes_that_could_alter_the_query():
    client = CftcClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])))
    with pytest.raises(CftcError):
        client.reports("0886' OR '1'='1", date(2026, 1, 1))


def test_client_reports_http_errors():
    client = CftcClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(400, text="bad query")),
        sleep=lambda _s: None,
    )
    with pytest.raises(CftcError, match="400"):
        client.reports("088691", date(2026, 1, 1))


# --- metrics -------------------------------------------------------------------------------


def test_cot_index_uses_only_past_weeks_and_needs_half_a_year():
    gold = BY_SYMBOL["XAUUSD"]
    nets = list(range(0, 30_000, 1_000))  # steadily rising: 30 weeks
    points = series(gold, [report(gold.code, i, n) for i, n in enumerate(nets)])
    assert points[24].cot_index is None  # 25 weeks of history
    assert points[25].cot_index == 100.0  # newest is the max of its window
    assert points[-1].net == 29_000
    assert points[-1].net_pct_oi == 29.0


def test_yen_positioning_is_flipped_for_usdjpy():
    yen = BY_SYMBOL["USDJPY"]
    [point] = series(yen, [report(yen.code, 0, 20_000)])
    assert point.net == -20_000  # speculators long JPY = short USDJPY


# --- ingestion and API ---------------------------------------------------------------------


@pytest.fixture
def db_session(app):
    gen = app.dependency_overrides[get_session]()
    yield next(gen)
    gen.close()


def handler_for(rows_by_code):
    def handler(request: httpx.Request):
        where = request.url.params["$where"]
        code = where.split("'")[1]
        since = where.split("'")[3]
        rows = [r for r in rows_by_code.get(code, []) if r["report_date_as_yyyy_mm_dd"] >= since]
        offset = int(request.url.params["$offset"])
        return httpx.Response(200, json=rows[offset:])

    return handler


@pytest.fixture
def ingested(db_session):
    rows = {"088691": weekly_rows("088691", [i * 1_000 for i in range(40)])}
    client = CftcClient(transport=httpx.MockTransport(handler_for(rows)), sleep=lambda _s: None)
    return ingest_cftc.ingest(client, db_session, ["XAUUSD", "DOGE"], start=date(2025, 1, 1))


def test_ingest_results(ingested):
    by_symbol = {r.symbol: r for r in ingested}
    assert by_symbol["XAUUSD"].rows == 40
    assert by_symbol["DOGE"].error == "no CFTC contract mapped"


def test_incremental_ingest_rereads_only_recent_weeks(db_session, ingested):
    rows = {"088691": weekly_rows("088691", [i * 1_000 for i in range(41)])}
    client = CftcClient(transport=httpx.MockTransport(handler_for(rows)), sleep=lambda _s: None)
    [result] = ingest_cftc.ingest(client, db_session, ["XAUUSD"], start=date(2025, 1, 1))
    assert result.rows == 6  # the latest stored week and the four before it, plus the new one


def test_positioning_snapshot(ingested, client):
    [gold] = client.get("/v1/positioning").json()
    assert gold["symbol"] == "XAUUSD"
    assert gold["latest"]["reportDate"] == (TUESDAY + timedelta(weeks=39)).isoformat()
    assert gold["latest"]["net"] == 39_000
    assert gold["latest"]["cotIndex"] == 100.0
    assert gold["weeklyChange"] == 1_000


def test_positioning_as_of_respects_release_dates(ingested, client):
    tuesday = TUESDAY + timedelta(weeks=10)
    # On the Thursday after, that week's report is not public yet.
    thursday = client.get(
        "/v1/positioning", params={"asOf": (tuesday + timedelta(days=2)).isoformat()}
    )
    assert thursday.json()[0]["latest"]["reportDate"] == (tuesday - timedelta(weeks=1)).isoformat()
    friday = client.get(
        "/v1/positioning", params={"asOf": (tuesday + timedelta(days=3)).isoformat()}
    )
    assert friday.json()[0]["latest"]["reportDate"] == tuesday.isoformat()


def test_positioning_history(ingested, client):
    body = client.get("/v1/positioning/xauusd", params={"weeks": 10}).json()
    assert body["symbol"] == "XAUUSD"
    assert len(body["points"]) == 10
    assert body["points"][-1]["net"] == 39_000


def test_positioning_errors(client, ingested):
    assert client.get("/v1/positioning/DOGEUSD").status_code == 404
    assert client.get("/v1/positioning/EURUSD").status_code == 404  # mapped, not ingested
    assert client.get("/v1/positioning/XAUUSD", params={"weeks": 0}).status_code == 422
    assert client.get("/v1/positioning/XAU-USD").status_code == 422
