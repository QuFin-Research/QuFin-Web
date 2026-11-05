"""OECD leading indicators and confidence: multi-series SDMX, release dates and ingest."""

from datetime import date

import httpx
import pytest

from app.connectors.oecd import CLI_FLOW, OecdClient
from app.connectors.sdmx import SdmxError
from app.data.indicator_concepts import concept_for
from app.data.macro_catalog import BY_ID, OECD_SERIES
from app.data.oecd_calendar import oecd_release
from app.data.scorecard_catalog import SCORED
from app.jobs import ingest_oecd
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def message(series, periods):
    """series: list of ((area, measure), values)."""
    areas = sorted({a for (a, _), _ in series})
    measures = sorted({m for (_, m), _ in series})
    return {
        "data": {
            "dataSets": [
                {
                    "series": {
                        f"{areas.index(a)}:0:{measures.index(m)}": {
                            "observations": {str(i): [v] for i, v in enumerate(values)}
                        }
                        for (a, m), values in series
                    }
                }
            ],
            "structure": {
                "dimensions": {
                    "series": [
                        {"id": "REF_AREA", "values": [{"id": a} for a in areas]},
                        {"id": "FREQ", "values": [{"id": "M"}]},
                        {"id": "MEASURE", "values": [{"id": m} for m in measures]},
                    ],
                    # Periods out of time order, as the OECD sends them.
                    "observation": [{"values": [{"id": p} for p in periods]}],
                }
            },
        }
    }


def client_for(bodies, seen=None):
    """bodies: OECD area -> message; the request path names the area."""

    def handler(request: httpx.Request):
        key = request.url.path.rsplit("/", 1)[-1]
        if seen is not None:
            seen.append(key)
        area = key.split(".")[0]
        return httpx.Response(200, json=bodies[area])

    return OecdClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_one_series_is_read_with_periods_in_time_order():
    body = message([(("JPN", "LI"), [101.2, 100.9])], ["2026-09", "2026-08"])
    s = client_for({"JPN": body}).series(CLI_FLOW, "JPN.M.LI.IX..AA.IX..H")
    assert s.observations == [(date(2026, 8, 1), 100.9), (date(2026, 9, 1), 101.2)]
    assert s.dimensions["REF_AREA"] == "JPN"
    with pytest.raises(SdmxError):
        client_for({}).series("OECD/../x", "JPN.M.LI")


def test_oecd_release_dates_err_late():
    assert oecd_release(date(2026, 9, 1)) == date(2026, 11, 16)  # 15 Nov 2026 is a Sunday
    assert oecd_release(date(2026, 12, 1)) == date(2027, 2, 15)


def test_oecd_series_are_leading_unscored_and_share_us_names():
    assert not set(OECD_SERIES) & set(SCORED)
    assert all(BY_ID[s].cycle == "leading" and BY_ID[s].change == "diff" for s in OECD_SERIES)
    assert concept_for("JP", "OECD_CLI_JPN") == concept_for("US", "USALOLITOAASTSAM")
    assert concept_for("CA", "OECD_CCI_CAN") == concept_for("US", "UMCSENT")
    assert not any(area == "USA" for area, _ in OECD_SERIES.values())  # US comes from FRED


def test_ingest_requests_each_series_alone_and_rejects_gaps(db_session):  # noqa: F811
    seen = []
    bodies = {
        "JPN": message([(("JPN", "LI"), [100.9, 101.2])], ["2026-08", "2026-09"]),
        # A broken response: June and September with the months between missing.
        "POL": message([(("POL", "BCICP"), [97.0, 98.4])], ["2026-06", "2026-09"]),
    }
    results = ingest_oecd.ingest(
        client_for(bodies, seen),
        db_session,
        ["OECD_CLI_JPN", "OECD_BCI_POL", "UNRATE"],
        today=date(2026, 11, 6),
        sleep=lambda _s: None,
    )
    by_id = {r.series_id: r for r in results}
    assert seen == ["JPN.M.LI.IX..AA.IX..H", "POL.M.BCICP.IX..AA.IX..H"]
    assert by_id["OECD_CLI_JPN"].rows == 2
    assert "2 months missing" in by_id["OECD_BCI_POL"].error
    assert by_id["UNRATE"].error == "not an OECD series in the catalog"
    store = MacroStore(db_session)
    assert store.get_series("OECD_BCI_POL") is None  # nothing stored from a broken response
    # August is dated 15 October; September, not yet due by the rule, from the day it was seen.
    assert [v.value for v in store.as_of("OECD_CLI_JPN", date(2026, 10, 15))] == [100.9]
    assert [v.value for v in store.as_of("OECD_CLI_JPN", date(2026, 11, 6))] == [100.9, 101.2]
    assert store.get_series("OECD_CLI_JPN").country == "JP"
