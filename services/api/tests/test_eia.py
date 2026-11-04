"""EIA weekly petroleum: release dates, connector and point-in-time storage without vintages."""

from datetime import UTC, date, datetime

import httpx
import pytest

from app.connectors.eia import EiaClient, EiaError
from app.data.eia_calendar import wpsr_release_date
from app.data.indicator_concepts import NON_FRED_ALLOWED
from app.data.macro_catalog import CATALOG
from app.jobs import ingest_eia
from app.stores.macro import MacroStore, SeriesMeta
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

KEY = "eia-test-key-0123456789"


# --- release calendar -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("week_ending", "released"),
    [
        (date(2026, 10, 23), date(2026, 10, 28)),  # normal week: the Wednesday after
        (date(2026, 1, 16), date(2026, 1, 22)),  # Martin Luther King Day Monday: Thursday
        (date(2026, 11, 20), date(2026, 11, 25)),  # Thanksgiving Thursday comes after: Wednesday
        (date(2026, 12, 25), date(2026, 12, 30)),  # holiday on the week's own Friday: no delay
    ],
)
def test_weekly_petroleum_release_dates(week_ending, released):
    assert wpsr_release_date(week_ending) == released


def test_release_is_never_before_the_wednesday():
    friday = date(2015, 1, 2)
    while friday < date(2027, 1, 1):
        assert (wpsr_release_date(friday) - friday).days >= 5
        friday = date.fromordinal(friday.toordinal() + 7)


# --- connector --------------------------------------------------------------------------------


def _rows(weeks):
    # The API returns newest first, ignoring sort parameters.
    return [
        {
            "period": d.isoformat(),
            "value": v,
            "units": "MBBL",
            "series-description": "U.S. Ending Stocks excluding SPR of Crude Oil (MBBL)",
        }
        for d, v in sorted(weeks, reverse=True)
    ]


WEEKS = [(date(2026, 10, 2), 400.0), (date(2026, 10, 9), 405.0), (date(2026, 10, 16), 410.0)]


def client_for(rows, page=2, **kwargs):
    def handler(request: httpx.Request):
        assert request.url.path == "/v2/seriesid/PET.WCESTUS1.W"
        assert request.url.params["api_key"] == KEY
        offset = int(request.url.params["offset"])
        return httpx.Response(
            200, json={"response": {"total": len(rows), "data": rows[offset : offset + page]}}
        )

    from app.connectors import eia

    return EiaClient(
        KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None, **kwargs
    ), eia


def test_client_pages_sorts_filters_and_names_units(monkeypatch):
    client, eia = client_for(_rows(WEEKS))
    monkeypatch.setattr(eia, "PAGE_LIMIT", 2)
    series = client.weekly_petroleum("WCESTUS1", start=date(2026, 10, 9))
    assert series.observations == [(date(2026, 10, 9), 405.0), (date(2026, 10, 16), 410.0)]
    assert series.units == "Thousand Barrels"
    assert "Crude Oil" in series.title


def test_client_errors_never_include_the_key():
    client = EiaClient(
        KEY,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                403, json={"error": {"message": "An invalid api_key was supplied."}}
            )
        ),
        sleep=lambda _s: None,
    )
    with pytest.raises(EiaError) as err:
        client.weekly_petroleum("WCESTUS1")
    assert "invalid api_key" in str(err.value)
    assert KEY not in str(err.value)


def test_client_rejects_ids_that_could_alter_the_path():
    client, _ = client_for([])
    with pytest.raises(EiaError):
        client.weekly_petroleum("WCESTUS1/../x")


# --- point-in-time storage ----------------------------------------------------------------------


def _meta():
    return SeriesMeta(
        "WCESTUS1",
        "eia",
        "Crude stocks",
        "Thousand Barrels",
        "Weekly",
        "NSA",
        "US",
        "energy",
        datetime(2026, 10, 1, tzinfo=UTC),
    )


def test_first_load_dates_weeks_by_release_and_revisions_become_vintages(db_session):  # noqa: F811
    store = MacroStore(db_session)
    today = date(2026, 10, 30)
    assert store.record_latest(_meta(), WEEKS, wpsr_release_date, today) == 3
    # Known only from its release Wednesday.
    assert [v.value for v in store.as_of("WCESTUS1", date(2026, 10, 20))] == [400.0, 405.0]
    assert store.record_latest(_meta(), WEEKS, wpsr_release_date, today) == 0  # unchanged

    revised = [*WEEKS[:2], (date(2026, 10, 16), 412.0)]
    assert store.record_latest(_meta(), revised, wpsr_release_date, date(2026, 11, 2)) == 1
    before = store.as_of("WCESTUS1", date(2026, 10, 31))
    after = store.as_of("WCESTUS1", date(2026, 11, 2))
    assert before[-1].value == 410.0  # what was published then
    assert after[-1].value == 412.0  # the revision, from the day it was seen
    assert [r.value for r in store.revisions("WCESTUS1", date(2026, 10, 16))] == [410.0, 412.0]
    [summary] = store.list_series()
    assert (summary.first_period, summary.last_period, summary.vintage_rows) == (
        date(2026, 10, 2),
        date(2026, 10, 16),
        4,
    )


def test_ingest_job_loads_catalog_eia_series_only(db_session):  # noqa: F811
    client, _ = client_for(_rows(WEEKS), page=10)
    results = ingest_eia.ingest(
        client, db_session, ["WCESTUS1", "UNRATE"], start=date(2026, 1, 1), today=date(2026, 11, 2)
    )
    by_id = {r.series_id: r for r in results}
    assert by_id["WCESTUS1"].rows == 3
    assert by_id["UNRATE"].error == "not an EIA series in the catalog"
    meta = MacroStore(db_session).get_series("WCESTUS1")
    assert meta.source_name == "U.S. Energy Information Administration"
    assert meta.release_name == "Weekly Petroleum Status Report"


def test_every_non_fred_us_series_has_a_recorded_reason_and_no_stale_exemptions():
    non_fred = {e.id for e in CATALOG if e.country == "US" and e.source != "fred"}
    assert non_fred == set(NON_FRED_ALLOWED)


def test_release_check_names_eia_as_the_source(db_session):  # noqa: F811
    from app.jobs.check_data import check_macro

    MacroStore(db_session).record_latest(_meta(), WEEKS, wpsr_release_date, date(2026, 10, 30))
    sources = {c.id: c.source for c in check_macro(db_session, date(2026, 10, 30))}
    assert sources["WCESTUS1"] == "eia"
    assert sources["UNRATE"] == "fred"
