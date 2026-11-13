"""BIS: connector (API v2, many economies per request), series ids, release dates, ingest."""

import json
from datetime import date

import httpx
import pytest

from app.connectors.bis import BisClient
from app.connectors.sdmx import SdmxError, SdmxSeries
from app.data.bis_calendar import monthly_release, quarterly_release
from app.data.bis_ids import BIS_COUNTRIES, BIS_SERIES, KNOWN_GAPS, MEASURES
from app.data.indicator_concepts import SERIES_CONCEPTS, concept_for
from app.data.macro_catalog import BY_ID
from app.data.series_units import SERIES_UNITS
from app.jobs import ingest_bis
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

# --- real BIS release calendar (bis.org/statistics/relcal.htm, read 12 Nov 2026) ---------------
# The last release listed for each reference period (policy rates are refreshed weekly).
CBPOL_LAST = (
    ("2024-03", date(2024, 4, 25)),
    ("2024-04", date(2024, 5, 30)),
    ("2024-05", date(2024, 6, 27)),
    ("2024-06", date(2024, 7, 25)),
    ("2024-07", date(2024, 8, 29)),
    ("2024-08", date(2024, 9, 26)),
    ("2024-09", date(2024, 10, 31)),
    ("2024-10", date(2024, 11, 28)),
    ("2024-11", date(2024, 12, 19)),
    ("2024-12", date(2025, 1, 30)),
    ("2025-01", date(2025, 2, 27)),
    ("2025-02", date(2025, 3, 27)),
    ("2025-03", date(2025, 4, 24)),
    ("2025-04", date(2025, 5, 28)),
    ("2025-05", date(2025, 6, 26)),
    ("2025-06", date(2025, 7, 31)),
    ("2025-07", date(2025, 8, 28)),
    ("2025-08", date(2025, 9, 25)),
    ("2025-09", date(2025, 10, 30)),
    ("2025-10", date(2025, 11, 27)),
    ("2025-11", date(2025, 12, 23)),
    ("2025-12", date(2026, 1, 29)),
    ("2026-01", date(2026, 2, 26)),
    ("2026-02", date(2026, 3, 26)),
    ("2026-03", date(2026, 4, 30)),
    ("2026-04", date(2026, 5, 28)),
    ("2026-05", date(2026, 6, 25)),
    ("2026-06", date(2026, 7, 31)),
    ("2026-07", date(2026, 8, 27)),
    ("2026-08", date(2026, 9, 24)),
)
EER = (
    ("2024-03", date(2024, 4, 18)),
    ("2024-04", date(2024, 5, 16)),
    ("2024-05", date(2024, 6, 20)),
    ("2024-06", date(2024, 7, 25)),
    ("2024-07", date(2024, 8, 15)),
    ("2024-08", date(2024, 9, 19)),
    ("2024-09", date(2024, 10, 17)),
    ("2024-10", date(2024, 11, 21)),
    ("2024-11", date(2024, 12, 19)),
    ("2024-12", date(2025, 1, 23)),
    ("2025-01", date(2025, 2, 20)),
    ("2025-02", date(2025, 3, 20)),
    ("2025-03", date(2025, 4, 17)),
    ("2025-04", date(2025, 5, 22)),
    ("2025-05", date(2025, 6, 19)),
    ("2025-06", date(2025, 7, 24)),
    ("2025-07", date(2025, 8, 28)),
    ("2025-08", date(2025, 9, 18)),
    ("2025-09", date(2025, 10, 23)),
    ("2025-10", date(2025, 11, 20)),
    ("2025-11", date(2025, 12, 18)),
    ("2025-12", date(2026, 1, 22)),
    ("2026-01", date(2026, 2, 19)),
    ("2026-02", date(2026, 3, 19)),
    ("2026-03", date(2026, 4, 23)),
    ("2026-04", date(2026, 5, 21)),
    ("2026-05", date(2026, 6, 18)),
    ("2026-06", date(2026, 7, 23)),
    ("2026-07", date(2026, 8, 20)),
    ("2026-08", date(2026, 9, 17)),
)
CREDIT = (
    ("2023-Q1", date(2023, 9, 18)),
    ("2023-Q2", date(2023, 12, 4)),
    ("2023-Q3", date(2024, 3, 4)),
    ("2023-Q4", date(2024, 6, 10)),
    ("2024-Q1", date(2024, 9, 16)),
    ("2024-Q2", date(2024, 12, 10)),
    ("2024-Q3", date(2025, 3, 11)),
    ("2024-Q4", date(2025, 6, 16)),
    ("2025-Q1", date(2025, 9, 15)),
    ("2025-Q2", date(2025, 12, 8)),
    ("2025-Q3", date(2026, 3, 16)),
    ("2025-Q4", date(2026, 6, 15)),
    ("2026-Q1", date(2026, 9, 14)),
)


def month_start(label: str) -> date:
    return date(int(label[:4]), int(label[5:]), 1)


def quarter_start(label: str) -> date:
    return date(int(label[:4]), 3 * int(label[-1]) - 2, 1)


@pytest.mark.parametrize("calendar", [CBPOL_LAST, EER])
def test_monthly_release_is_never_before_the_bis_publishes(calendar):
    for label, released in calendar:
        derived = monthly_release(month_start(label))
        assert derived >= released, (label, derived, released)
        assert derived.weekday() < 5
        assert (derived - released).days <= 20  # late, but not absurdly so


def test_quarterly_release_is_never_before_the_bis_publishes():
    for label, released in CREDIT:
        derived = quarterly_release(quarter_start(label))
        assert derived >= released, (label, derived, released)
        assert derived.weekday() < 5
        assert (derived - released).days <= 30


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        (date(2026, 10, 1), date(2026, 11, 30)),  # November 30 is a Monday
        (date(2026, 11, 1), date(2026, 12, 31)),
        (date(2026, 12, 1), date(2027, 1, 29)),  # January 31 is a Sunday
        (date(2024, 1, 1), date(2024, 2, 29)),  # leap year
    ],
)
def test_monthly_release_is_the_last_weekday_of_the_next_month(period, expected):
    assert monthly_release(period) == expected


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        (date(2026, 1, 1), date(2026, 9, 30)),  # Q1 ends March, released by September
        (date(2026, 4, 1), date(2026, 12, 31)),
        (date(2026, 7, 1), date(2027, 3, 31)),
        (date(2026, 10, 1), date(2027, 6, 30)),
    ],
)
def test_quarterly_release_is_the_last_weekday_of_the_sixth_month_after(period, expected):
    assert quarterly_release(period) == expected


# --- series ids ---------------------------------------------------------------------------------


def test_every_bis_series_is_in_the_catalog_with_a_unit_a_cycle_and_a_name():
    assert len(BIS_SERIES) == 153  # 115 + 12 (DE, FR, IT) + Kuwait policy rate + 25 property prices
    for series_id, (code, _area) in BIS_SERIES.items():
        entry = BY_ID[series_id]
        assert entry.source == "bis"
        assert entry.country == BIS_COUNTRIES[series_id]
        assert entry.cycle == MEASURES[code].cycle
        assert entry.change == MEASURES[code].change
        assert series_id in SERIES_UNITS
        assert concept_for(entry.country, series_id) is not None, series_id
        assert entry.licence_note and "BIS" in entry.licence_note


def test_economies_left_out_stay_out():
    ids = set(BIS_SERIES)
    # The US is carried by FRED with vintages, except property prices: FRED's copy of the BIS index
    # (not seasonally adjusted, with vintages) ran a quarter behind the BIS on 13 Nov 2026.
    assert not {i for i in ids if i.endswith("_US") and not i.startswith("BIS_SPP_")}
    assert not {i for i in ids if i.endswith("_RU")}
    assert "BIS_CBPOL_DE" not in ids and "BIS_CBPOL_FR" not in ids  # the ECB rate, rule 16
    assert "BIS_CBPOL_KW" in ids and "BIS_CBPOL_QA" not in ids
    assert "BIS_CBPOL_XM" not in ids  # the ECB deposit rate is stored already (rule 16)
    assert "BIS_CBPOL_SG" not in ids
    assert "BIS_CBPOL_AE" not in ids
    assert "BIS_CREDIT_AE" not in ids
    assert BIS_COUNTRIES["BIS_REER_XM"] == "EA"


def test_bis_does_not_duplicate_a_concept_in_any_economy():
    seen = {}
    for (country, series_id), concept in SERIES_CONCEPTS.items():
        if series_id in BIS_SERIES:
            key = (country, concept)
            assert key not in seen, f"{series_id} repeats {seen[key]}"
            seen[key] = series_id
    # And policy rates do not collide with the euro area's stored deposit rate.
    assert ("EA", "policy_rate") in {
        (c, k) for (c, s), k in SERIES_CONCEPTS.items() if s == "FM.D.U2.EUR.4F.KR.DFR.LEV"
    }


# --- connector ----------------------------------------------------------------------------------


def message(areas, periods, values, *, dimension="REF_AREA", extra_dimensions=()):
    """An SDMX-JSON message with one series per area over the same periods."""
    series = {}
    for i, _area in enumerate(areas):
        key = ":".join(["0"] * len(extra_dimensions) + [str(i)])
        series[key] = {
            "attributes": [],
            "observations": {str(j): [values[i][j], 0, 0, None] for j in range(len(periods))},
        }
    return {
        "data": {
            "dataSets": [{"series": series}],
            "structure": {
                "dimensions": {
                    "series": [
                        *[{"id": d, "values": [{"id": "X"}]} for d in extra_dimensions],
                        {"id": dimension, "values": [{"id": a} for a in areas]},
                    ],
                    "observation": [{"values": [{"id": p} for p in periods]}],
                },
                "attributes": {"series": []},
            },
        }
    }


def client_for(handler, **kwargs):
    return BisClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None, **kwargs)


def test_client_asks_v2_for_json_in_the_header_and_reads_every_economy():
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(
            200,
            json=message(["GB", "JP"], ["2026-09", "2026-10"], [["3.75", "3.75"], ["1", "1.25"]]),
        )

    series = client_for(handler).many("WS_CBPOL", "M.GB+JP", date(2026, 1, 1))
    request = seen[0]
    assert request.url.path == "/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.GB+JP"
    assert request.url.params["startPeriod"] == "2026-01-01"
    assert "format" not in request.url.params  # v2 answers 406 to format=jsondata
    assert request.headers["accept"].startswith("application/vnd.sdmx.data+json")
    assert "QuFin" in request.headers["user-agent"]  # identifies us, not a bare library string
    by_area = {s.dimensions["REF_AREA"]: s for s in series}
    assert by_area["JP"].observations == [(date(2026, 9, 1), 1.0), (date(2026, 10, 1), 1.25)]


def test_client_rejects_flows_and_keys_that_could_alter_the_path():
    client = client_for(lambda r: httpx.Response(200, json={}))
    with pytest.raises(SdmxError):
        client.many("WS_CBPOL/../x", "M.GB")
    with pytest.raises(SdmxError):
        client.many("WS_CBPOL", "M.GB?x=1")


def test_client_keeps_raw_file_names_short_and_the_body_in_the_raw_zone(tmp_path):
    from app.stores.raw_zone import RawZone

    areas = "+".join(["GB", "JP", "CA", "AU", "NZ", "CH", "NO", "SE", "DK", "CZ"] * 6)
    client = BisClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=message(["GB"], ["2026-10"], [["1"]]))
        ),
        sleep=lambda _s: None,
        raw=RawZone(tmp_path),
    )
    client.many("WS_CBPOL", f"M.{areas}")
    [saved] = list((tmp_path / "bis").rglob("*.json"))
    assert len(saved.name) < 80
    assert b"REF_AREA" in saved.read_bytes()


def test_client_errors_name_the_status_without_the_url():
    client = client_for(lambda r: httpx.Response(404, json={"title": "No data"}))
    with pytest.raises(SdmxError) as err:
        client.many("WS_CBPOL", "M.ZZ")
    assert "404" in str(err.value)
    assert "stats.bis.org" not in str(err.value)


# --- ingest -------------------------------------------------------------------------------------


class FakeBis:
    """Stands in for BisClient: returns the series it is given for each flow and key."""

    def __init__(self, series=None, error=None):
        self.series, self.error, self.calls = series or {}, error, []

    def many(self, flow, key, start=None):
        self.calls.append((flow, key, start))
        if self.error:
            raise self.error
        return self.series.get(flow, [])


def monthly(area, first, count, value=1.0, dimension="REF_AREA", attributes=None):
    year, month = first
    obs = []
    for i in range(count):
        m = month - 1 + i
        obs.append((date(year + m // 12, m % 12 + 1, 1), value + i))
    return SdmxSeries("f", "k", "t", attributes or {}, obs, {dimension: area})


def quarterly(area, first, count):
    year, quarter = first
    obs = []
    for i in range(count):
        q = quarter - 1 + i
        obs.append((date(year + q // 4, 3 * (q % 4) + 1, 1), 100.0 + i))
    return SdmxSeries("f", "k", "t", {}, obs, {"BORROWERS_CTY": area})


TODAY = date(2026, 11, 12)


def stored(db_session, series_id):  # noqa: F811
    store = MacroStore(db_session)
    return store, {v.period: v for v in store.as_of(series_id, date(2030, 1, 1))}


def test_one_request_per_measure_loads_every_economy_and_dates_by_release(db_session):  # noqa: F811
    client = FakeBis(
        {"WS_CBPOL": [monthly("GB", (2026, 7), 4, 3.0), monthly("JP", (2026, 7), 4, 1.0)]}
    )
    results = ingest_bis.ingest(
        client,
        db_session,
        ["BIS_CBPOL_GB", "BIS_CBPOL_JP"],
        date(2026, 1, 1),
        TODAY,
        lambda _s: None,
    )
    assert [r.error for r in results] == [None, None]
    assert len(client.calls) == 1
    flow, key, start = client.calls[0]
    assert (flow, key, start) == ("WS_CBPOL", "M.GB+JP", date(2026, 1, 1))
    store, rows = stored(db_session, "BIS_CBPOL_GB")
    # July's rate was public by the end of August; the newest month is dated the day it is seen.
    assert rows[date(2026, 7, 1)].realtime_start == date(2026, 8, 31)
    assert rows[date(2026, 10, 1)].realtime_start == TODAY
    assert store.as_of("BIS_CBPOL_GB", date(2026, 8, 30)) == []
    meta = {s.meta.id: s.meta for s in store.list_series()}["BIS_CBPOL_GB"]
    assert meta.source == "bis"
    assert meta.units == "Percent per annum"
    assert meta.country == "GB"
    assert "Bank for International Settlements" in meta.source_name


def test_credit_series_are_read_by_borrower_country_and_dated_by_the_quarterly_rule(db_session):  # noqa: F811
    client = FakeBis({"WS_CREDIT_GAP": [quarterly("GB", (2025, 3), 4)]})
    ingest_bis.ingest(client, db_session, ["BIS_CREDIT_GB"], date(2025, 1, 1), TODAY)
    assert client.calls[0][1] == "Q.GB.P.A.A"
    _store, rows = stored(db_session, "BIS_CREDIT_GB")
    assert rows[date(2025, 7, 1)].realtime_start == date(2026, 3, 31)  # Q3 2025: March 2026
    assert rows[date(2026, 1, 1)].realtime_start == date(2026, 9, 30)  # released 14 Sep
    assert rows[date(2026, 4, 1)].realtime_start == TODAY  # not due until December


def test_each_economy_is_matched_to_its_own_series(db_session):  # noqa: F811
    client = FakeBis(
        {
            "WS_EER": [
                monthly("JP", (2026, 8), 2, 70.0, attributes={"UNIT_MEASURE": "Index, 2020 = 100"}),
                monthly(
                    "GB", (2026, 8), 2, 111.0, attributes={"UNIT_MEASURE": "Index, 2020 = 100"}
                ),
            ]
        }
    )
    ingest_bis.ingest(
        client, db_session, ["BIS_REER_GB", "BIS_REER_JP"], date(2026, 1, 1), TODAY, lambda _s: None
    )
    _s, gb = stored(db_session, "BIS_REER_GB")
    _s, jp = stored(db_session, "BIS_REER_JP")
    assert gb[date(2026, 8, 1)].value == 111.0
    assert jp[date(2026, 8, 1)].value == 70.0


def test_a_missing_month_is_a_partial_response_and_loads_nothing(db_session):  # noqa: F811
    partial = monthly("GB", (2026, 1), 8)
    partial = SdmxSeries(
        "f", "k", "t", {}, [o for o in partial.observations if o[0].month != 4], {"REF_AREA": "GB"}
    )
    results = ingest_bis.ingest(
        FakeBis({"WS_CBPOL": [partial]}), db_session, ["BIS_CBPOL_GB"], date(2026, 1, 1), TODAY
    )
    assert "1 periods missing" in results[0].error
    assert MacroStore(db_session).list_series() == []


def test_a_missing_quarter_is_a_partial_response(db_session):  # noqa: F811
    q = quarterly("GB", (2024, 1), 6)
    q = SdmxSeries(
        "f", "k", "t", {}, [o for o in q.observations if o[0] != date(2024, 7, 1)], q.dimensions
    )
    results = ingest_bis.ingest(
        FakeBis({"WS_CREDIT_GAP": [q]}), db_session, ["BIS_CREDIT_GB"], date(2024, 1, 1), TODAY
    )
    assert "1 periods missing" in results[0].error


def test_japans_documented_policy_rate_gaps_are_accepted_and_others_are_not(db_session):  # noqa: F811
    (a0, b0), (a1, b1), (a2, b2) = KNOWN_GAPS["BIS_CBPOL_JP"]
    assert (a0, b0) == (date(1999, 3, 1), date(2000, 7, 1))  # found loading from 1990
    assert (a1, b1) == (date(2001, 4, 1), date(2006, 2, 1))
    assert (a2, b2) == (date(2013, 5, 1), date(2016, 8, 1))
    edges = [(date(2001, 3, 1), 0.1), (date(2006, 3, 1), 0.25), (date(2006, 4, 1), 0.25)]
    declared = SdmxSeries("f", "k", "t", {}, edges, {"REF_AREA": "JP"})
    results = ingest_bis.ingest(
        FakeBis({"WS_CBPOL": [declared]}), db_session, ["BIS_CBPOL_JP"], date(2000, 1, 1), TODAY
    )
    assert results[0].error is None
    # An undeclared missing month in the same series is a partial response.
    undeclared = SdmxSeries(
        "f", "k", "t", {}, [(date(2020, 1, 1), 0.1), (date(2020, 3, 1), 0.1)], {"REF_AREA": "JP"}
    )
    results = ingest_bis.ingest(
        FakeBis({"WS_CBPOL": [undeclared]}), db_session, ["BIS_CBPOL_JP"], date(2000, 1, 1), TODAY
    )
    assert "1 periods missing" in results[0].error
    # The same gap for another economy is a failure: the allowance is Japan's alone.
    other = SdmxSeries("f", "k", "t", {}, edges, {"REF_AREA": "GB"})
    results = ingest_bis.ingest(
        FakeBis({"WS_CBPOL": [other]}), db_session, ["BIS_CBPOL_GB"], date(2000, 1, 1), TODAY
    )
    assert "periods missing" in results[0].error


def test_changed_units_fail_the_load(db_session):  # noqa: F811
    series = monthly("GB", (2026, 8), 2, attributes={"UNIT_MEASURE": "Index, 2010 = 100"})
    results = ingest_bis.ingest(
        FakeBis({"WS_EER": [series]}), db_session, ["BIS_REER_GB"], date(2026, 1, 1), TODAY
    )
    assert "expected 'Index, 2020 = 100'" in results[0].error


def test_an_economy_the_bis_did_not_return_is_reported(db_session):  # noqa: F811
    client = FakeBis({"WS_CBPOL": [monthly("GB", (2026, 8), 2)]})
    results = ingest_bis.ingest(
        client,
        db_session,
        ["BIS_CBPOL_GB", "BIS_CBPOL_JP"],
        date(2026, 1, 1),
        TODAY,
        lambda _s: None,
    )
    by_id = {r.series_id: r for r in results}
    assert by_id["BIS_CBPOL_GB"].error is None
    assert "no series for JP" in by_id["BIS_CBPOL_JP"].error


def test_a_failed_request_marks_every_series_of_that_measure_and_continues(db_session):  # noqa: F811
    class Flaky(FakeBis):
        def many(self, flow, key, start=None):
            if flow == "WS_CBPOL":
                raise SdmxError("boom")
            return [monthly("GB", (2026, 8), 2, attributes={"UNIT_MEASURE": "Index, 2020 = 100"})]

    pauses = []
    results = ingest_bis.ingest(
        Flaky(),
        db_session,
        ["BIS_CBPOL_GB", "BIS_CBPOL_JP", "BIS_REER_GB"],
        date(2026, 1, 1),
        TODAY,
        pauses.append,
    )
    by_id = {r.series_id: r for r in results}
    assert "boom" in by_id["BIS_CBPOL_GB"].error and "boom" in by_id["BIS_CBPOL_JP"].error
    assert by_id["BIS_REER_GB"].error is None
    assert pauses == [ingest_bis.PAUSE_SECONDS]  # one pause between the two requests


def test_a_refusal_stops_the_run_so_we_never_hammer_a_source_that_said_no(db_session):  # noqa: F811
    class Refusing(FakeBis):
        def many(self, flow, key, start=None):
            self.calls.append(flow)
            raise SdmxError("bis returned 429: Too Many Requests")

    client = Refusing()
    results = ingest_bis.ingest(
        client,
        db_session,
        ["BIS_CBPOL_GB", "BIS_REER_GB", "BIS_CREDIT_GB"],
        date(2026, 1, 1),
        TODAY,
        lambda _s: None,
    )
    assert client.calls == ["WS_CBPOL"]  # the other two measures were never requested
    assert all(r.error for r in results) and len(results) == 3


def test_client_honours_retry_after_and_gives_up_after_its_retries():
    waits, calls = [], []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "7"}, text="slow down")

    client = BisClient(
        transport=httpx.MockTransport(handler), sleep=waits.append, max_retries=3, min_interval=0
    )
    with pytest.raises(SdmxError, match="429"):
        client.many("WS_CBPOL", "M.GB")
    assert waits == [7.0, 7.0, 7.0] and len(calls) == 4


def test_ids_outside_the_catalog_are_rejected_without_a_request(db_session):  # noqa: F811
    client = FakeBis()
    results = ingest_bis.ingest(
        client, db_session, ["BIS_CBPOL_US", "UNRATE"], date(2026, 1, 1), TODAY
    )
    assert [r.error for r in results] == ["not a BIS series in the catalog"] * 2
    assert client.calls == []


def test_null_observations_are_not_stored_as_values(db_session):  # noqa: F811
    series = monthly("GB", (2026, 8), 3)
    series = SdmxSeries(
        "f",
        "k",
        "t",
        {},
        [series.observations[0], (date(2026, 9, 1), None), series.observations[2]],
        series.dimensions,
    )
    # A null in the middle leaves a missing month: reported, not filled.
    results = ingest_bis.ingest(
        FakeBis({"WS_CBPOL": [series]}), db_session, ["BIS_CBPOL_GB"], date(2026, 1, 1), TODAY
    )
    assert "1 periods missing" in results[0].error


def test_ingest_bis_command_is_registered():
    from app.cli import main

    with pytest.raises(SystemExit) as stop:
        main(["ingest-bis", "--help"])
    assert stop.value.code == 0


def test_every_measure_has_a_verified_flow_and_a_known_area_dimension():
    assert json.dumps(sorted(MEASURES)) == json.dumps(
        ["CBPOL", "CREDGAP", "CREDIT", "NEER", "REER", "SPP"]
    )
    for measure in MEASURES.values():
        assert "{areas}" in measure.key
        assert measure.area_dimension in {"REF_AREA", "BORROWERS_CTY"}
