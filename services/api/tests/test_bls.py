"""BLS API v2: connector (keyless or keyed, windows, retries), periods, release lags, ingest."""

import json
from datetime import date, timedelta

import httpx
import pytest

from app.connectors.bls import BlsClient, BlsError, _period_to_date
from app.data.macro_catalog import BY_ID
from app.jobs import ingest_bls
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

ECI = "CIS1010000000000I"


def message(rows, status="REQUEST_SUCCEEDED", messages=None, series_id=ECI):
    """A BLS v2 response. A real series object holds only `seriesID` and `data`."""
    series = [{"seriesID": series_id, "data": rows}] if rows is not None else []
    return {"status": status, "message": messages or [], "Results": {"series": series}}


def row(year, period, value):
    return {"year": str(year), "period": period, "periodName": "x", "value": value}


def client_for(handler, **kwargs):
    return BlsClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None, **kwargs)


# --- periods ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "period", "expected"),
    [
        ("2026", "M09", "2026-09-01"),
        ("2026", "Q03", "2026-07-01"),
        ("2026", "Q01", "2026-01-01"),
        ("2026", "S02", "2026-07-01"),
        ("2026", "A01", "2026-01-01"),
        ("2026", "M13", None),  # BLS's annual-average pseudo month
        ("2026", "Q05", None),
    ],
)
def test_periods_are_dated_by_their_first_day(year, period, expected):
    assert _period_to_date(year, period) == expected


# --- connector --------------------------------------------------------------------------------


def test_series_object_without_a_status_is_parsed_and_sorted():
    """BLS series objects carry no status of their own (regression: every fetch failed)."""
    rows = [row(2026, "Q03", "178.574"), row(2026, "Q02", "177.178"), row(2026, "Q01", "-")]
    client = client_for(lambda r: httpx.Response(200, json=message(rows)))
    assert client.series(ECI, 2026, 2026) == [
        (date(2026, 1, 1), None),
        (date(2026, 4, 1), 177.178),
        (date(2026, 7, 1), 178.574),
    ]


def test_long_histories_are_fetched_in_windows_the_plan_allows():
    asked = []

    def handler(request):
        body = json.loads(request.content)
        asked.append((body["startyear"], body["endyear"]))
        return httpx.Response(200, json=message([row(body["startyear"], "Q01", "1.0")]))

    client_for(handler).series(ECI, 2000, 2026)
    assert asked == [("2000", "2009"), ("2010", "2019"), ("2020", "2026")]
    asked.clear()
    client_for(handler, api_key="k").series(ECI, 2000, 2026)
    assert asked == [("2000", "2019"), ("2020", "2026")]


def test_works_without_a_key_and_never_sends_one():
    seen = []

    def handler(request):
        seen.append((request.headers.get("registrationkey"), json.loads(request.content)))
        return httpx.Response(200, json=message([row(2026, "Q03", "1.0")]))

    client_for(handler).series(ECI, 2026, 2026)
    assert seen[0][0] is None
    assert "registrationkey" not in seen[0][1]


def test_unknown_series_fails_with_the_message_and_never_echoes_the_key():
    def handler(request):
        return httpx.Response(
            200, json=message(None, messages=["Series does not exist for Series BAD (key sekret)"])
        )

    client = client_for(handler, api_key="sekret")
    with pytest.raises(BlsError) as err:
        client.series("BAD", 2026, 2026)
    assert "does not exist" in str(err.value)
    assert "sekret" not in str(err.value)


def test_failed_request_status_is_reported_not_called_a_missing_series():
    client = client_for(
        lambda r: httpx.Response(
            200, json=message(None, "REQUEST_NOT_PROCESSED", ["daily threshold reached"])
        )
    )
    with pytest.raises(BlsError, match="daily threshold"):
        client.series(ECI, 2026, 2026)


def test_a_series_with_no_observations_at_all_is_an_error():
    client = client_for(lambda r: httpx.Response(200, json=message([])))
    with pytest.raises(BlsError, match="no observations"):
        client.series(ECI, 2026, 2026)


def test_rate_limits_and_server_errors_are_retried():
    answers = [
        httpx.Response(429, headers={"retry-after": "1"}),
        httpx.Response(503),
        httpx.Response(200, json=message([row(2026, "Q03", "1.0")])),
    ]
    waits = []
    client = BlsClient(
        transport=httpx.MockTransport(lambda r: answers.pop(0)), sleep=waits.append, min_interval=0
    )
    assert client.series(ECI, 2026, 2026) == [(date(2026, 7, 1), 1.0)]
    assert waits == [1.0, 2.0]


def test_http_errors_are_raised_without_the_url():
    client = client_for(lambda r: httpx.Response(400, json={"message": "bad"}))
    with pytest.raises(BlsError) as err:
        client.series(ECI, 2026, 2026)
    assert "400" in str(err.value)
    assert "api.bls.gov" not in str(err.value)


def test_response_that_is_not_json_is_an_error():
    client = client_for(lambda r: httpx.Response(200, content=b"<html>"))
    with pytest.raises(BlsError, match="not JSON"):
        client.series(ECI, 2026, 2026)


# --- catalog and release dates ----------------------------------------------------------------


def test_only_series_that_exist_at_bls_are_in_the_catalog():
    """Both original ids were rejected by BLS ("Series does not exist")."""
    assert [s.id for s in BY_ID.values() if s.source == "bls"] == [ECI]
    assert set(ingest_bls.SERIES) == {ECI}
    assert "CIU0000000000" not in BY_ID
    assert "JTS0000000000" not in BY_ID


def test_eci_release_lag_errs_late_for_every_quarter():
    """ECI comes out near the end of the month after the quarter (Jan, Apr, Jul, Oct)."""
    lag = timedelta(days=ingest_bls.RELEASE_LAG_DAYS[ECI])
    earliest_real_release = {
        date(2026, 1, 1): date(2026, 4, 28),
        date(2026, 4, 1): date(2026, 7, 28),
        date(2026, 7, 1): date(2026, 10, 28),
        date(2026, 10, 1): date(2027, 1, 28),
    }
    for quarter_start, release in earliest_real_release.items():
        assert quarter_start + lag > release


# --- ingest -----------------------------------------------------------------------------------


class FakeClient:
    def __init__(self, observations=None, error=None):
        self.observations, self.error, self.calls = observations or [], error, []

    def series(self, series_id, start_year=2000, end_year=None):
        self.calls.append((series_id, start_year))
        if self.error:
            raise self.error
        return self.observations


OBS = [(date(2025, 10, 1), 177.0), (date(2026, 1, 1), 177.5), (date(2026, 4, 1), 178.0)]


def test_ingest_honours_start_and_dates_periods_by_the_eci_lag(db_session):  # noqa: F811
    client = FakeClient(OBS)
    results = ingest_bls.ingest(
        client, db_session, [ECI], start=date(2026, 1, 1), today=date(2026, 12, 31)
    )
    assert results[0].error is None
    assert results[0].rows == 2
    assert client.calls == [(ECI, 2026)]  # the start year, not the default 2000
    store = MacroStore(db_session)
    released = {v.period: v.realtime_start for v in store.as_of(ECI, date(2026, 12, 31))}
    assert set(released) == {date(2026, 1, 1), date(2026, 4, 1)}  # October 2025 trimmed
    assert released[date(2026, 1, 1)] == date(2026, 5, 6)  # 125 days after the quarter start
    # Nothing is readable before the release.
    assert store.as_of(ECI, date(2026, 5, 5)) == []


def test_ingest_dates_a_period_never_later_than_today(db_session):  # noqa: F811
    ingest_bls.ingest(FakeClient(OBS), db_session, [ECI], today=date(2026, 6, 1))
    seen = MacroStore(db_session).as_of(ECI, date(2026, 6, 1))
    assert {v.period: v.realtime_start for v in seen}[date(2026, 4, 1)] == date(2026, 6, 1)


def test_ingest_rejects_ids_outside_the_catalog_and_keeps_going(db_session):  # noqa: F811
    results = ingest_bls.ingest(
        FakeClient(OBS),
        db_session,
        ["CIU0000000000", ECI],
        today=date(2026, 12, 31),
        sleep=lambda _s: None,
    )
    assert results[0].error == "not a BLS series in the catalog"
    assert results[1].error is None


def test_one_failing_series_is_reported_and_rolled_back(db_session):  # noqa: F811
    results = ingest_bls.ingest(
        FakeClient(error=BlsError("boom")), db_session, [ECI], today=date(2026, 12, 31)
    )
    assert results[0].rows is None
    assert "boom" in results[0].error
    assert MacroStore(db_session).list_series() == []


def test_ingest_bls_command_is_registered():
    from app.cli import main

    with pytest.raises(SystemExit) as stop:
        main(["ingest-bls", "--help"])
    assert stop.value.code == 0
