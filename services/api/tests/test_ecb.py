"""Shared SDMX client, ECB connector, euro area release dates and ingest."""

from datetime import date

import httpx
import pytest

from app.connectors.ecb import EcbClient
from app.connectors.sdmx import SdmxError, parse_data_message, parse_period
from app.data.ecb_calendar import hicp_release, m3_release, policy_rate_release
from app.data.indicator_concepts import concept_for
from app.data.macro_catalog import CATALOG
from app.jobs import ingest_ecb
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

HICP = "HICP.M.U2.N.000000.4D0.ANR"


def message(
    periods, values, title="HICP - Total - Annual rate of change", unit="Percentage change"
):
    return {
        "dataSets": [
            {
                "series": {
                    "0:0:0": {
                        "attributes": [0, 0],
                        "observations": {str(i): [v] for i, v in enumerate(values)},
                    }
                }
            }
        ],
        "structure": {
            "dimensions": {"observation": [{"values": [{"id": p} for p in periods]}]},
            "attributes": {
                "series": [
                    {"id": "TITLE", "values": [{"name": title}]},
                    {"id": "UNIT", "values": [{"id": "PCCH", "name": unit}]},
                ]
            },
        },
    }


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("2026-11-05", date(2026, 11, 5)),
        ("2026-10", date(2026, 10, 1)),
        ("2026-Q3", date(2026, 7, 1)),
        ("2026", date(2026, 1, 1)),
    ],
)
def test_sdmx_periods_become_first_days(period, expected):
    assert parse_period(period) == expected


def test_parse_data_message_reads_values_title_and_attributes():
    s = parse_data_message(
        "HICP", "M.U2.N.000000.4D0.ANR", message(["2026-09", "2026-10"], [3.8, 4])
    )
    assert s.observations == [(date(2026, 9, 1), 3.8), (date(2026, 10, 1), 4.0)]
    assert s.title.startswith("HICP")
    assert s.attributes["UNIT"] == "Percentage change"


def test_parse_rejects_anything_but_one_series():
    body = message(["2026-10"], [4])
    body["dataSets"][0]["series"]["0:0:1"] = body["dataSets"][0]["series"]["0:0:0"]
    with pytest.raises(SdmxError, match="expected one series"):
        parse_data_message("HICP", "M.U2.*", body)


def test_client_queries_the_ecb_and_validates_keys():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.url.path, dict(request.url.params)))
        return httpx.Response(200, json=message(["2026-10"], [4]))

    client = EcbClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    client.series("HICP", "M.U2.N.000000.4D0.ANR", date(2020, 1, 1))
    assert seen == [
        (
            "/service/data/HICP/M.U2.N.000000.4D0.ANR",
            {"format": "jsondata", "startPeriod": "2020-01-01"},
        )
    ]
    with pytest.raises(SdmxError):
        client.series("HICP", "M.U2/../x")


def test_client_reports_the_sources_error_without_the_url():
    client = EcbClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(404, json={"title": "Not Found", "detail": "No Series"})
        ),
        sleep=lambda _s: None,
    )
    with pytest.raises(SdmxError, match="Not Found") as err:
        client.series("HICP", "M.U2.N.000000.4D0.ANR")
    assert "data-api.ecb.europa.eu" not in str(err.value)


def test_euro_area_release_dates_err_late():
    assert policy_rate_release(date(2026, 11, 5)) == date(2026, 11, 5)
    assert hicp_release(date(2026, 10, 1)) == date(2026, 11, 20)  # final, not the flash
    assert hicp_release(date(2026, 8, 1)) == date(2026, 9, 21)  # 20 Sep 2026 is a Sunday
    assert m3_release(date(2026, 9, 1)) == date(2026, 10, 30)  # last business day of October
    assert m3_release(date(2026, 12, 1)) == date(2027, 1, 29)


def test_euro_area_series_share_concept_names_with_the_us_and_are_not_scored():
    from app.data.scorecard_catalog import SCORED

    ea = [e for e in CATALOG if e.country == "EA"]
    assert {concept_for("EA", e.id).name for e in ea} >= {
        concept_for("US", "FEDFUNDS").name,
        concept_for("US", "CPILFESL").name,
    }
    assert not {e.id for e in ea} & set(SCORED)
    hicp = next(e for e in ea if e.id == HICP)
    assert hicp.published_as_change and hicp.change == "diff"  # an annual rate: never re-changed


def test_flash_value_is_stored_today_and_the_final_figure_becomes_a_revision(db_session):  # noqa: F811
    def client_for(values):
        return EcbClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=message(["2026-09", "2026-10"], values))
            ),
            sleep=lambda _s: None,
        )

    [flash] = ingest_ecb.ingest(client_for([3.8, 4.0]), db_session, [HICP], today=date(2026, 11, 6))
    assert flash.rows == 2
    store = MacroStore(db_session)
    # September is dated at its final release (20 Oct); October's flash from the day it was seen.
    assert [v.value for v in store.as_of(HICP, date(2026, 10, 19))] == []
    assert [v.value for v in store.as_of(HICP, date(2026, 11, 6))] == [3.8, 4.0]
    [final] = ingest_ecb.ingest(
        client_for([3.8, 4.1]), db_session, [HICP], today=date(2026, 11, 20)
    )
    assert final.rows == 1
    assert [r.value for r in store.revisions(HICP, date(2026, 10, 1))] == [4.0, 4.1]
    assert store.get_series(HICP).source_name == "Eurostat"
