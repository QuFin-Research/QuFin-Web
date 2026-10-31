"""FRED/ALFRED connector (Federal Reserve Bank of St. Louis).

Fetches series metadata and the full vintage history (ALFRED real-time periods), so the store
can answer "what was published on day D". API docs: https://fred.stlouisfed.org/docs/api/fred/

The API key travels as a query parameter (FRED supports nothing else), so it is kept out of
logs and error messages: httpx's request logging is turned down and errors never echo URLs.
"""

import logging
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

import httpx
import truststore

from app.stores.macro import Vintage

# httpx logs every request URL at INFO, which would include api_key.
logging.getLogger("httpx").setLevel(logging.WARNING)

# Earliest real-time date ALFRED accepts; asking from here returns every vintage.
ALL_VINTAGES_START = "1776-07-04"
ALL_VINTAGES_END = "9999-12-31"
PAGE_LIMIT = 100_000
VINTAGE_DATES_LIMIT = 10_000
# ALFRED rejects an observations request whose real-time period spans more than 2,000 vintage
# dates, and its count can include a date its vintage list does not, so stay well under.
MAX_VINTAGES_PER_REQUEST = 1_900
RETRY_STATUSES = {429, 500, 502, 503, 504}


class FredError(Exception):
    pass


@dataclass(frozen=True)
class FredSeries:
    id: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    last_updated: datetime | None


def _parse_last_updated(value: str | None) -> datetime | None:
    """FRED sends e.g. '2026-10-15 07:46:02-05' (hour-only UTC offset)."""
    if not value:
        return None
    if len(value) >= 3 and value[-3] in "+-" and value[-2:].isdigit():
        value += "00"
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")
    except ValueError:
        return None


def _parse_value(value: str) -> float | None:
    return None if value in (".", "") else float(value)


class FredClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.stlouisfed.org/fred",
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=30.0,
            transport=transport,
            # Trust the operating system's certificate store, so corporate TLS inspection
            # proxies that are trusted on the machine work too.
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )
        self._max_retries = max_retries
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FredClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, str | int]) -> dict:
        query = {**params, "api_key": self._api_key, "file_type": "json"}
        for attempt in range(self._max_retries + 1):
            try:
                res = self._client.get(path, params=query)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    raise FredError(
                        f"FRED request to {path} failed: {type(exc).__name__}"
                    ) from None
                self._sleep(2**attempt)
                continue
            if res.status_code in RETRY_STATUSES and attempt < self._max_retries:
                self._sleep(float(res.headers.get("retry-after", 2**attempt)))
                continue
            if res.status_code != 200:
                raise FredError(f"FRED {path} returned {res.status_code}: {_error_message(res)}")
            return res.json()
        raise FredError(f"FRED {path} kept failing")  # pragma: no cover

    def series(self, series_id: str) -> FredSeries:
        body = self._get("/series", {"series_id": series_id})
        items = body.get("seriess") or []
        if not items:
            raise FredError(f"FRED has no series {series_id}")
        s = items[0]
        return FredSeries(
            id=s["id"],
            title=s.get("title", ""),
            units=s.get("units", ""),
            frequency=s.get("frequency", ""),
            seasonal_adjustment=s.get("seasonal_adjustment", ""),
            last_updated=_parse_last_updated(s.get("last_updated")),
        )

    def vintage_dates(self, series_id: str) -> list[date]:
        """Every date on which ALFRED recorded a new release of the series, oldest first."""
        result: list[date] = []
        while True:
            body = self._get(
                "/series/vintagedates",
                {"series_id": series_id, "limit": VINTAGE_DATES_LIMIT, "offset": len(result)},
            )
            page = body.get("vintage_dates") or []
            result.extend(date.fromisoformat(d) for d in page)
            if not page or len(result) >= int(body.get("count", 0)):
                return result

    def vintages(self, series_id: str, observation_start: date | None = None) -> list[Vintage]:
        """Every published value of every period since `observation_start`, all vintages.

        ALFRED serves at most MAX_VINTAGES_PER_REQUEST vintage dates per request (daily market
        series have thousands), so the real-time axis is fetched in windows and rows that a
        window boundary split are joined again.
        """
        dates = self.vintage_dates(series_id)
        windows = [
            (
                ALL_VINTAGES_START if i == 0 else dates[i].isoformat(),
                ALL_VINTAGES_END
                if i + MAX_VINTAGES_PER_REQUEST >= len(dates)
                else (dates[i + MAX_VINTAGES_PER_REQUEST] - timedelta(days=1)).isoformat(),
            )
            for i in range(0, max(len(dates), 1), MAX_VINTAGES_PER_REQUEST)
        ]
        rows: list[Vintage] = []
        for realtime_start, realtime_end in windows:
            rows.extend(
                self._observations(series_id, realtime_start, realtime_end, observation_start)
            )
        return _join_split_rows(rows) if len(windows) > 1 else rows

    def _observations(
        self, series_id: str, realtime_start: str, realtime_end: str, observation_start: date | None
    ) -> list[Vintage]:
        params: dict[str, str | int] = {
            "series_id": series_id,
            "realtime_start": realtime_start,
            "realtime_end": realtime_end,
            "limit": PAGE_LIMIT,
        }
        if observation_start is not None:
            params["observation_start"] = observation_start.isoformat()

        result: list[Vintage] = []
        while True:
            body = self._get("/series/observations", {**params, "offset": len(result)})
            page = body.get("observations") or []
            result.extend(
                Vintage(
                    period=date.fromisoformat(o["date"]),
                    realtime_start=date.fromisoformat(o["realtime_start"]),
                    realtime_end=date.fromisoformat(o["realtime_end"]),
                    value=_parse_value(o["value"]),
                )
                for o in page
            )
            if not page or len(result) >= int(body.get("count", 0)):
                return result


def _join_split_rows(rows: list[Vintage]) -> list[Vintage]:
    """ALFRED clips real-time periods to the requested window; undo that at window edges."""
    joined: list[Vintage] = []
    for row in sorted(rows, key=lambda v: (v.period, v.realtime_start)):
        last = joined[-1] if joined else None
        if (
            last is not None
            and last.period == row.period
            and last.value == row.value
            and last.realtime_end + timedelta(days=1) == row.realtime_start
        ):
            joined[-1] = replace(last, realtime_end=row.realtime_end)
        else:
            joined.append(row)
    return joined


def _error_message(res: httpx.Response) -> str:
    try:
        return str(res.json().get("error_message", "")).strip() or res.reason_phrase
    except ValueError:
        return res.reason_phrase
