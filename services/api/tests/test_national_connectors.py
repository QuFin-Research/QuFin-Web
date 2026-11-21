"""The Bank of Canada, ABS, RBA and Bank of England connectors: parsing, requests, refusals."""

from datetime import date

import httpx
import pytest

from app.connectors.abs import AbsClient
from app.connectors.bankofcanada import BankOfCanadaClient, BankOfCanadaError
from app.connectors.base import USER_AGENT
from app.connectors.boe import BoeClient, BoeError, parse_csv
from app.connectors.rba import RbaClient, RbaError, parse_table


def mock(handler):
    return {"transport": httpx.MockTransport(handler), "sleep": lambda _s: None}


# --- Bank of Canada Valet ---------------------------------------------------------------------


def valet(*items):
    return {"observations": [{"d": d, "V1": {"v": v}} for d, v in items]}


def test_valet_returns_the_observations_oldest_first_and_names_itself():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=valet(("2026-10-01", "2.50"), ("2026-09-01", "2.25")))

    with BankOfCanadaClient(**mock(handler)) as client:
        got = client.series("V1", date(2026, 1, 1))
    assert got == [(date(2026, 9, 1), 2.25), (date(2026, 10, 1), 2.5)]
    assert seen[0].url.path == "/valet/observations/V1/json"
    assert seen[0].url.params["start_date"] == "2026-01-01"
    assert seen[0].headers["user-agent"] == USER_AGENT


def test_valet_skips_empty_values_and_rejects_nothing_or_bad_ids():
    ok = lambda _r: httpx.Response(200, json=valet(("2026-10-01", ""), ("2026-09-01", "1.0")))  # noqa: E731
    with BankOfCanadaClient(**mock(ok)) as client:
        assert client.series("V1") == [(date(2026, 9, 1), 1.0)]
        with pytest.raises(BankOfCanadaError, match="Not a valid"):
            client.series("../x")
    empty = lambda _r: httpx.Response(200, json={"observations": []})  # noqa: E731
    with (
        BankOfCanadaClient(**mock(empty)) as client,
        pytest.raises(BankOfCanadaError, match="no obs"),
    ):
        client.series("V1")


def test_a_refusal_stops_the_client_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403, text="blocked")

    with BankOfCanadaClient(**mock(handler)) as client:
        for _ in range(2):
            with pytest.raises(BankOfCanadaError):
                client.series("V1")
    assert len(calls) == 1  # the second call never left the machine (rule 28)


# --- RBA tables -------------------------------------------------------------------------------

RBA_CSV = (
    "﻿D3 MONETARY AGGREGATES\n"
    "Title,Currency,Broad money\n"
    "Frequency,Monthly,Monthly\n"
    "Publication date,30-Oct-2026,30-Oct-2026\n"
    "Series ID,DMACN,DMABMS\n"
    "31/07/2026,0.8,3500.1\n"
    "31/08/2026,,3506.9\n"
    "30/09/2026,0.9,3513.2\n"
    "Notes,,\n"
)


def test_an_rba_table_gives_each_series_and_the_publication_date():
    published, series = parse_table(RBA_CSV)
    assert published == date(2026, 10, 30)
    assert series["DMABMS"][-1] == (date(2026, 9, 30), 3513.2)
    assert [p for p, _ in series["DMACN"]] == [date(2026, 7, 31), date(2026, 9, 30)]  # a gap stays


def test_the_rba_client_returns_one_series_from_the_start_date():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, text=RBA_CSV)

    with RbaClient(**mock(handler)) as client:
        published, observations = client.series("d3", "DMABMS", date(2026, 8, 1))
        assert published == date(2026, 10, 30) and len(observations) == 2
        with pytest.raises(RbaError, match="no series"):
            client.series("d3", "NOPE")
        with pytest.raises(RbaError, match="no observations"):
            client.series("d3", "DMABMS", date(2027, 1, 1))
        with pytest.raises(RbaError, match="Not a valid"):
            client.series("../d3", "DMABMS")
    assert seen[0] == "/statistics/tables/csv/d3-data.csv"
    with pytest.raises(RbaError, match="no Series ID"):
        parse_table("Title,x\n")


# --- Bank of England --------------------------------------------------------------------------

BOE_CSV = "DATE,LPMVWYR\n31 Jul 2026,97630\n31 Aug 2026,98113\n30 Sep 2026,\n"


def test_the_boe_csv_gives_monthly_values_dated_by_the_first_of_the_month():
    assert parse_csv(BOE_CSV, "LPMVWYR") == [
        (date(2026, 7, 1), 97630.0),
        (date(2026, 8, 1), 98113.0),
    ]
    for bad in ("", "DATE,OTHER\n", "DATE,LPMVWYR\n"):
        with pytest.raises(BoeError):
            parse_csv(bad, "LPMVWYR")
    with pytest.raises(BoeError, match="Unreadable"):
        parse_csv("DATE,LPMVWYR\nsoon,1\n", "LPMVWYR")


def test_the_boe_client_asks_for_one_code_from_a_date():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, text=BOE_CSV)

    with BoeClient(**mock(handler)) as client:
        assert len(client.series("LPMVWYR", date(2026, 6, 1))) == 2
        with pytest.raises(BoeError, match="Not a valid"):
            client.series("lower")
    params = seen[0].url.params
    assert params["SeriesCodes"] == "LPMVWYR" and params["Datefrom"] == "01/Jun/2026"


# --- ABS --------------------------------------------------------------------------------------


def test_the_abs_client_reads_an_sdmx_series_from_its_own_base_url():
    body = {
        "data": {
            "dataSets": [{"series": {"0:0": {"observations": {"0": [102.31], "1": [103.64]}}}}],
            "structure": {
                "dimensions": {
                    "series": [
                        {"id": "FREQ", "values": [{"id": "Q"}]},
                        {"id": "INDEX", "values": [{"id": "10001"}]},
                    ],
                    "observation": [
                        {"values": [{"id": "2026-Q2"}, {"id": "2026-Q3"}]},
                    ],
                },
                "attributes": {"series": []},
            },
        }
    }
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=body)

    with AbsClient(**mock(handler)) as client:
        series = client.series("ABS,CPI,2.0.0", "1.10001.10.50.Q", date(2026, 1, 1))
    assert series.observations == [(date(2026, 4, 1), 102.31), (date(2026, 7, 1), 103.64)]
    assert seen[0].url.host == "data.api.abs.gov.au"
    assert seen[0].url.path == "/rest/data/ABS,CPI,2.0.0/1.10001.10.50.Q"
