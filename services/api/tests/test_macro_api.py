"""Point-in-time macro store, FRED ingestion and the /v1/macro endpoints."""

from datetime import date

import httpx
import pytest
from sqlalchemy.orm import Session

from app.connectors.fred import FredClient
from app.jobs.ingest_fred import ingest
from app.stores.db import get_session

# UNRATE for Aug and Sep 2026 with a revision: Aug first printed 4.3 on Sep 5,
# revised to 4.2 on Oct 3, when Sep was first printed at 4.1.
VINTAGES = [
    {
        "date": "2026-08-01",
        "realtime_start": "2026-09-05",
        "realtime_end": "2026-10-02",
        "value": "4.3",
    },
    {
        "date": "2026-08-01",
        "realtime_start": "2026-10-03",
        "realtime_end": "9999-12-31",
        "value": "4.2",
    },
    {
        "date": "2026-09-01",
        "realtime_start": "2026-10-03",
        "realtime_end": "9999-12-31",
        "value": "4.1",
    },
]


def fred_handler(request: httpx.Request):
    series_id = request.url.params["series_id"]
    if series_id != "UNRATE":
        return httpx.Response(400, json={"error_message": "The series does not exist."})
    if request.url.path.endswith("/vintagedates"):
        return httpx.Response(200, json={"count": 2, "vintage_dates": ["2026-09-05", "2026-10-03"]})
    if request.url.path.endswith("/observations"):
        return httpx.Response(200, json={"count": len(VINTAGES), "observations": VINTAGES})
    return httpx.Response(
        200,
        json={
            "seriess": [
                {
                    "id": "UNRATE",
                    "title": "Unemployment Rate",
                    "units": "Percent",
                    "frequency": "Monthly",
                    "seasonal_adjustment": "Seasonally Adjusted",
                    "last_updated": "2026-10-03 07:48:02-05",
                }
            ]
        },
    )


@pytest.fixture
def db_session(app) -> Session:
    gen = app.dependency_overrides[get_session]()
    session = next(gen)
    yield session
    gen.close()


@pytest.fixture
def ingested(app, db_session):
    client = FredClient("k", transport=httpx.MockTransport(fred_handler), sleep=lambda _s: None)
    return ingest(client, db_session, ["UNRATE", "CPIAUCSL", "NOTINCATALOG"])


def test_ingest_reports_each_series(ingested):
    by_id = {r.series_id: r for r in ingested}
    assert by_id["UNRATE"].rows == 3
    assert "does not exist" in by_id["CPIAUCSL"].error
    assert by_id["NOTINCATALOG"].error == "not in the macro catalog"


def test_reingest_replaces_rather_than_duplicates(app, db_session, ingested, client):
    fred = FredClient("k", transport=httpx.MockTransport(fred_handler), sleep=lambda _s: None)
    ingest(fred, db_session, ["UNRATE"])
    [summary] = client.get("/v1/macro/series").json()
    assert summary["vintageRows"] == 3


def test_list_series(ingested, client):
    [summary] = client.get("/v1/macro/series").json()
    assert summary["id"] == "UNRATE"
    assert summary["dimension"] == "labour"
    assert summary["country"] == "US"
    assert summary["firstPeriod"] == "2026-08-01"
    assert summary["lastPeriod"] == "2026-09-01"


def values(body):
    return [(o["period"], o["value"]) for o in body["observations"]]


def test_latest_values_by_default(ingested, client):
    body = client.get("/v1/macro/series/UNRATE").json()
    assert body["asOf"] is None
    assert values(body) == [("2026-08-01", 4.2), ("2026-09-01", 4.1)]


def test_point_in_time_view_hides_later_releases_and_revisions(ingested, client):
    # On Sep 20 only the first print of August existed.
    body = client.get("/v1/macro/series/unrate", params={"asOf": "2026-09-20"}).json()
    assert values(body) == [("2026-08-01", 4.3)]
    assert body["observations"][0]["realtimeStart"] == "2026-09-05"

    # Before anything was published there is nothing to see.
    assert values(client.get("/v1/macro/series/UNRATE", params={"asOf": "2026-09-01"}).json()) == []

    # The day of the revision.
    on_release = client.get("/v1/macro/series/UNRATE", params={"asOf": "2026-10-03"}).json()
    assert values(on_release) == [("2026-08-01", 4.2), ("2026-09-01", 4.1)]


def test_period_range(ingested, client):
    body = client.get("/v1/macro/series/UNRATE", params={"start": "2026-09-01"}).json()
    assert values(body) == [("2026-09-01", 4.1)]
    bad = client.get("/v1/macro/series/UNRATE", params={"start": "2026-09-01", "end": "2026-08-01"})
    assert bad.status_code == 422


def test_revision_history(ingested, client):
    body = client.get("/v1/macro/series/UNRATE/revisions", params={"period": "2026-08-01"}).json()
    assert body["revisions"] == [
        {"realtimeStart": "2026-09-05", "realtimeEnd": "2026-10-02", "value": 4.3},
        {"realtimeStart": "2026-10-03", "realtimeEnd": None, "value": 4.2},
    ]
    missing = client.get("/v1/macro/series/UNRATE/revisions", params={"period": "2001-01-01"})
    assert missing.status_code == 404


def test_validation_and_unknown_series(client):
    assert client.get("/v1/macro/series/UNRATE").status_code == 404
    assert client.get("/v1/macro/series/UN RATE").status_code == 422
    assert client.get("/v1/macro/series/UNRATE", params={"asOf": "yesterday"}).status_code == 422
    assert client.get("/v1/macro/series/UNRATE/revisions").status_code == 422


def test_store_as_of_directly(db_session, ingested):
    from app.stores.macro import MacroStore

    store = MacroStore(db_session)
    assert [v.value for v in store.as_of("UNRATE", date(2026, 10, 2))] == [4.3]


def test_market_series_history_before_the_archive_is_dated_by_release_lag():
    from datetime import timedelta

    from app.jobs.ingest_fred import date_pre_archive_periods
    from app.stores.macro import OPEN_END, Vintage

    archive = date(2005, 6, 28)
    old = [Vintage(date(2005, 6, d), archive, OPEN_END, 3.0) for d in (1, 2, 27)]
    # After archiving began each day was released the next day.
    new = [
        Vintage(archive + timedelta(days=i), archive + timedelta(days=i + 1), OPEN_END, 3.1)
        for i in range(1, 30)
    ]
    dated = {v.period: v.realtime_start for v in date_pre_archive_periods(old + new)}
    assert dated[date(2005, 6, 1)] == date(2005, 6, 2)
    assert dated[date(2005, 6, 2)] == date(2005, 6, 3)
    # Released after the archive date by the lag rule, so it keeps the archive date.
    assert dated[date(2005, 6, 27)] == date(2005, 6, 28)
    assert dated[archive + timedelta(days=1)] == archive + timedelta(days=2)
