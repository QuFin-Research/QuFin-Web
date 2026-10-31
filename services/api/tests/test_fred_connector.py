"""FRED/ALFRED connector against recorded-shape responses (no network)."""

from datetime import UTC, date, datetime

import httpx
import pytest

from app.connectors import fred
from app.connectors.fred import FredClient, FredError

KEY = "test-key-0123456789"

SERIES = {
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
}


def obs(period, start, end, value):
    return {"date": period, "realtime_start": start, "realtime_end": end, "value": value}


def client_for(handler, **kwargs):
    return FredClient(KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None, **kwargs)


def test_series_metadata():
    def handler(request: httpx.Request):
        assert request.url.path == "/fred/series"
        assert request.url.params["series_id"] == "UNRATE"
        assert request.url.params["api_key"] == KEY
        assert request.url.params["file_type"] == "json"
        return httpx.Response(200, json=SERIES)

    info = client_for(handler).series("UNRATE")
    assert info.title == "Unemployment Rate"
    assert info.last_updated == datetime(2026, 10, 3, 12, 48, 2, tzinfo=UTC)


def test_vintages_request_all_real_time_periods_and_page():
    pages = [
        {
            "count": 3,
            "observations": [
                obs("2026-08-01", "2026-09-05", "2026-10-02", "4.3"),
                obs("2026-08-01", "2026-10-03", "9999-12-31", "4.2"),
            ],
        },
        {"count": 3, "observations": [obs("2026-09-01", "2026-10-03", "9999-12-31", ".")]},
    ]
    seen = []

    def handler(request: httpx.Request):
        params = request.url.params
        if request.url.path.endswith("/vintagedates"):
            return httpx.Response(
                200, json={"count": 2, "vintage_dates": ["2026-09-05", "2026-10-03"]}
            )
        seen.append(int(params["offset"]))
        assert params["realtime_start"] == "1776-07-04"
        assert params["realtime_end"] == "9999-12-31"
        assert params["observation_start"] == "2026-01-01"
        return httpx.Response(200, json=pages[len(seen) - 1])

    vintages = client_for(handler).vintages("UNRATE", date(2026, 1, 1))
    assert seen == [0, 2]
    assert [(v.period, v.realtime_start, v.value) for v in vintages] == [
        (date(2026, 8, 1), date(2026, 9, 5), 4.3),
        (date(2026, 8, 1), date(2026, 10, 3), 4.2),
        (date(2026, 9, 1), date(2026, 10, 3), None),  # "." means no value
    ]


def test_vintages_split_the_real_time_axis_when_alfred_would_refuse(monkeypatch):
    # Five vintage dates, at most two per request: windows [start, d2-1], [d2, d4-1], [d4, end].
    monkeypatch.setattr(fred, "MAX_VINTAGES_PER_REQUEST", 2)
    monkeypatch.setattr(fred, "VINTAGE_DATES_LIMIT", 3)
    dates = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]
    # Jan 2 printed 1.0 on Jan 5 and never revised; Jan 5 printed 2.0, revised to 2.5 on Jan 7.
    history = [
        ("2026-01-02", "2026-01-05", "9999-12-31", "1.0"),
        ("2026-01-05", "2026-01-06", "2026-01-06", "2.0"),
        ("2026-01-05", "2026-01-07", "9999-12-31", "2.5"),
    ]
    windows = []

    def handler(request: httpx.Request):
        params = request.url.params
        if request.url.path.endswith("/vintagedates"):
            offset, limit = int(params["offset"]), int(params["limit"])
            return httpx.Response(
                200, json={"count": len(dates), "vintage_dates": dates[offset : offset + limit]}
            )
        lo, hi = params["realtime_start"], params["realtime_end"]
        windows.append((lo, hi))
        clipped = [
            obs(p, max(s, lo), min(e, hi), v) for p, s, e, v in history if s <= hi and e >= lo
        ]
        return httpx.Response(200, json={"count": len(clipped), "observations": clipped})

    vintages = client_for(handler).vintages("DGS2")
    assert windows == [
        ("1776-07-04", "2026-01-05"),
        ("2026-01-06", "2026-01-07"),
        ("2026-01-08", "9999-12-31"),
    ]
    assert [
        (str(v.period), str(v.realtime_start), str(v.realtime_end), v.value) for v in vintages
    ] == [
        ("2026-01-02", "2026-01-05", "9999-12-31", 1.0),
        ("2026-01-05", "2026-01-06", "2026-01-06", 2.0),
        ("2026-01-05", "2026-01-07", "9999-12-31", 2.5),
    ]


def test_retries_rate_limits_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"retry-after": "1"})
        return httpx.Response(200, json=SERIES)

    assert client_for(handler).series("UNRATE").id == "UNRATE"
    assert len(calls) == 3


def test_errors_never_include_the_api_key():
    def handler(request):
        return httpx.Response(
            400,
            json={"error_code": 400, "error_message": "Bad Request.  The series does not exist."},
        )

    with pytest.raises(FredError) as err:
        client_for(handler).series("NOPE")
    assert "does not exist" in str(err.value)
    assert KEY not in str(err.value)


def test_network_failures_give_up_without_leaking_the_url():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(FredError) as err:
        client_for(handler, max_retries=1).series("UNRATE")
    assert KEY not in str(err.value)
    assert "api_key" not in str(err.value)
