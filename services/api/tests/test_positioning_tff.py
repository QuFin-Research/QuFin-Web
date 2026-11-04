"""Traders in Financial Futures: financial contracts, read through leveraged funds."""

from datetime import date, timedelta

import httpx
import pytest

from app.connectors.cftc import CftcClient, CftcError, parse_financial_report
from app.data.positioning_catalog import BY_CODE, COT_CONTRACTS
from app.jobs import ingest_cftc
from app.jobs.check_data import check_positioning
from app.stores.positioning import CotReport, PositioningStore
from tests.test_positioning import TUESDAY, db_session, handler_for  # noqa: F401  (fixture)


def tff_row(code, report_date, lev_long, lev_short, am_long=300_000, am_short=200_000):
    return {
        "cftc_contract_market_code": code,
        "report_date_as_yyyy_mm_dd": f"{report_date.isoformat()}T00:00:00.000",
        "market_and_exchange_names": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "open_interest_all": "800000",
        "dealer_positions_long_all": "40000",
        "dealer_positions_short_all": "180000",
        "dealer_positions_spread_all": "10000",
        "asset_mgr_positions_long": str(am_long),
        "asset_mgr_positions_short": str(am_short),
        "asset_mgr_positions_spread": "50000",
        "lev_money_positions_long": str(lev_long),
        "lev_money_positions_short": str(lev_short),
        "lev_money_positions_spread": "28000",
        "other_rept_positions_long": "25000",
        "other_rept_positions_short": "19000",
        "other_rept_positions_spread": "4900",
        "nonrept_positions_long_all": "83000",
        "nonrept_positions_short_all": "54000",
    }


def weekly_tff(code, nets, start=TUESDAY):
    return [
        tff_row(code, start + timedelta(weeks=i), 100_000 + n, 100_000) for i, n in enumerate(nets)
    ]


def test_each_contract_comes_from_one_report_only():
    assert len(BY_CODE) == len(COT_CONTRACTS)
    financial = {c.symbol for c in COT_CONTRACTS if c.report == "tff"}
    assert {"EURUSD", "USDJPY", "USDX", "BTCUSD"} <= financial
    assert {"XAUUSD", "WTI", "NATGAS"}.isdisjoint(financial)  # commodities: not in TFF


def test_parse_financial_report_reads_every_group():
    r = parse_financial_report(tff_row("099741", TUESDAY, 125_046, 196_620))
    assert (r.lev_money_long, r.lev_money_short) == (125_046, 196_620)
    assert (r.asset_mgr_long, r.asset_mgr_short, r.dealer_short) == (300_000, 200_000, 180_000)
    assert r.release_date == date(2026, 1, 9)


def test_a_renamed_cftc_column_fails_instead_of_loading_zero():
    row = tff_row("099741", TUESDAY, 1, 2)
    del row["lev_money_positions_long"]
    with pytest.raises(CftcError, match="lev_money_positions_long"):
        parse_financial_report(row)


def test_financial_reports_come_from_the_tff_dataset():
    urls = []

    def handler(request: httpx.Request):
        urls.append(request.url.path)
        return httpx.Response(200, json=[])

    client = CftcClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    client.financial_reports("099741", TUESDAY)
    client.reports("088691", TUESDAY)
    assert urls == ["/resource/gpe5-46if.json", "/resource/6dca-aqww.json"]


@pytest.fixture
def ingested_tff(db_session):  # noqa: F811
    rows = {"097741": weekly_tff("097741", [i * 1_000 for i in range(30)])}
    client = CftcClient(transport=httpx.MockTransport(handler_for(rows)), sleep=lambda _s: None)
    return ingest_cftc.ingest(client, db_session, ["USDJPY"], start=date(2025, 1, 1))


def test_yen_follows_leveraged_funds_flipped_for_usdjpy(ingested_tff, client):
    assert ingested_tff[0].rows == 30
    [yen] = client.get("/v1/positioning").json()
    assert yen["report"] == "tff"
    assert yen["group"].startswith("Leveraged funds")
    assert yen["latest"]["net"] == -29_000  # funds long JPY = short USDJPY
    assert yen["latest"]["assetManagerNet"] == -100_000
    assert yen["latest"]["cotIndex"] == 0.0  # the most bearish USDJPY reading of the window
    history = client.get("/v1/positioning/USDJPY", params={"weeks": 5}).json()
    assert history["group"] == yen["group"]
    assert len(history["points"]) == 5


def test_financial_contracts_ignore_legacy_rows(db_session, ingested_tff):  # noqa: F811
    # A stray legacy row for the yen must not be mixed into its TFF history.
    stray = CotReport("097741", TUESDAY, TUESDAY, "YEN", 1, 999_999, 0, 0, 0, 0, 0, 0)
    store = PositioningStore(db_session)
    store.upsert([stray])
    yen = next(c for c in COT_CONTRACTS if c.symbol == "USDJPY")
    assert all(p.long < 999_999 for p in store.positions(yen))


def test_release_check_covers_financial_contracts(db_session, ingested_tff):  # noqa: F811
    today = TUESDAY + timedelta(weeks=29, days=4)
    checks = {c.id: c for c in check_positioning(db_session, today)}
    assert checks["USDJPY"].status.freshness.usable
    assert not checks["EURUSD"].status.freshness.usable  # mapped but never loaded
