"""IMF reserves: connector (JSON with a byte-order mark), periods, units, release dates, ingest."""

import json
from datetime import date

import httpx

from app.connectors.imf import IL_FLOW, ImfClient
from app.data.imf_calendar import imf_release
from app.data.indicator_concepts import concept_for
from app.data.macro_catalog import BY_ID
from app.data.reserves_ids import FRED_RESERVES, IMF_RESERVES, RESERVES
from app.data.scorecard_catalog import SCORED
from app.domain.units import classify
from app.jobs import ingest_imf
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def message(periods, values, area="CHE"):
    body = {
        "data": {
            "dataSets": [
                {
                    "series": {
                        "0:0:0:0": {"observations": {str(i): [v] for i, v in enumerate(values)}}
                    }
                }
            ],
            "structure": {
                "dimensions": {
                    "series": [
                        {"id": "COUNTRY", "values": [{"id": area}]},
                        {"id": "INDICATOR", "values": [{"id": "RXF11_REVS"}]},
                        {"id": "UNIT", "values": [{"id": "USD"}]},
                        {"id": "FREQUENCY", "values": [{"id": "M"}]},
                    ],
                    "observation": [{"values": [{"id": p} for p in periods]}],
                },
                "attributes": {
                    "series": [{"id": "SCALE", "values": [{"id": "6", "name": "Millions"}]}]
                },
            },
        }
    }
    # The IMF starts its JSON with a byte-order mark.
    return b"\xef\xbb\xbf" + json.dumps(body).encode()


def client_for(content, seen=None):
    def handler(request: httpx.Request):
        if seen is not None:
            seen.append((request.url.path, request.headers.get("accept", "")))
        return httpx.Response(200, content=content)

    return ImfClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_client_asks_for_json_and_reads_imf_months_despite_the_byte_order_mark():
    seen = []
    s = client_for(message(["2026-M09", "2026-M08"], [9.384e11, 9.675e11]), seen).series(
        IL_FLOW, "CHE.RXF11_REVS.USD.M"
    )
    assert s.observations == [(date(2026, 8, 1), 9.675e11), (date(2026, 9, 1), 9.384e11)]
    assert seen[0][0].endswith("/data/IMF.STA,IL,13.0.1/CHE.RXF11_REVS.USD.M")
    assert "sdmx.data+json" in seen[0][1]


def test_imf_release_dates_err_late():
    assert imf_release(date(2026, 9, 1)) == date(2026, 11, 30)
    assert imf_release(date(2026, 8, 1)) == date(2026, 10, 30)  # 31 Oct 2026 is a Saturday
    assert imf_release(date(2026, 11, 1)) == date(2027, 1, 29)


def test_reserves_come_from_fred_where_it_carries_them_and_share_one_name():
    assert not set(FRED_RESERVES) & {f"TRESEG{c}M052N" for c in IMF_RESERVES.values()}
    assert all(BY_ID[s].source == "fred" for s in FRED_RESERVES)  # rule 17
    assert all(BY_ID[s].source == "imf" for s in IMF_RESERVES)
    assert {"CN", "HK", "US"}.isdisjoint(RESERVES.values())  # stale, or not a gauge of the dollar
    names = {concept_for(c, s).name for s, c in RESERVES.items()}
    assert names == {"Foreign Exchange Reserves"}
    assert not set(RESERVES) & set(SCORED)
    assert all(BY_ID[s].change == "pct" and BY_ID[s].cycle == "coincident" for s in RESERVES)


def test_fred_dollars_are_usd_but_an_unqualified_dollar_elsewhere_is_not_guessed():
    assert classify("Millions of Dollars", "JP", "fred").currency == "USD"
    assert classify("U.S. Dollars", "CH", "imf").currency == "USD"
    assert classify("Millions of Dollars", "CA", "statcan").kind == "unknown"


def test_ingest_stores_dollars_unscaled_dated_by_release(db_session):  # noqa: F811
    client = client_for(message(["2026-M08", "2026-M09"], [9.675e11, 9.384e11]))
    results = ingest_imf.ingest(
        client,
        db_session,
        ["IMF_RES_CHE", "UNRATE"],
        today=date(2026, 11, 7),
        sleep=lambda _s: None,
    )
    assert results[0].rows == 2
    assert results[1].error == "not an IMF series in the catalog"
    store = MacroStore(db_session)
    meta = store.get_series("IMF_RES_CHE")
    assert (meta.units, meta.unit_kind, meta.currency, meta.country) == (
        "U.S. Dollars",
        "amount_currency",
        "USD",
        "CH",
    )
    # August is dated 30 October; September, not yet due by the rule, from the day it was seen.
    assert [v.value for v in store.as_of("IMF_RES_CHE", date(2026, 10, 30))] == [9.675e11]
    assert [v.value for v in store.as_of("IMF_RES_CHE", date(2026, 11, 7))] == [9.675e11, 9.384e11]
