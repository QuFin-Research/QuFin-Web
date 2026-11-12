"""BLS API v2 connector (Bureau of Labor Statistics), keyless for limited use.

Used only for what FRED does not carry (rule 17): the Employment Cost Index and other
BLS series FRED lacks. API docs: https://www.bls.gov/developers/

The API is a JSON POST; a registration key raises the daily limit but is not required
for a small number of series. Without a key, requests are rate-limited by BLS.
"""

import json
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.connectors.base import RETRY_STATUSES, HttpSource, SourceError, retry_delay

BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BlsError(SourceError):
    pass


def _period_to_date(year: str, period: str) -> str | None:
    """Convert BLS year + period (e.g. M01, Q01, S01, A01) to an ISO date string."""
    if period.startswith("M"):
        month = int(period[1:])
        if 1 <= month <= 12:
            return f"{year}-{month:02d}-01"
    elif period.startswith("Q"):
        q = int(period[1:])
        if 1 <= q <= 4:
            return f"{year}-{3 * q - 2:02d}-01"
    elif period.startswith("S"):
        s = int(period[1:])
        if s in (1, 2):
            return f"{year}-{6 * s - 5:02d}-01"
    elif period == "A01":
        return f"{year}-01-01"
    return None


class BlsClient(HttpSource):
    source = "bls"
    min_interval = 0.5  # rule 28: published: 50 requests per 10 s, 500 queries a day with a key
    error = BlsError

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        **kwargs: Any,
    ) -> None:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["registrationkey"] = api_key
        kwargs.setdefault("headers", headers)
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)
        self._api_key = api_key

    def describe_error(self, res: Any) -> str:
        try:
            body = res.json()
            return str(body.get("message") or body.get("error") or res.reason_phrase)
        except ValueError:
            return res.reason_phrase

    def series(
        self,
        series_id: str,
        start_year: int = 2000,
        end_year: int | None = None,
    ) -> list[tuple[date, float | None]]:
        """Fetch all observations for one BLS series id, oldest first.

        BLS returns current values (no vintages). Periods may be monthly (M01-M12),
        quarterly (Q01-Q04), semiannual (S01-S02) or annual (A01).

        BLS caps the span of one query (20 years with a registration key, 10 without),
        so long histories are fetched in year windows and merged.
        """
        end_year = end_year or datetime.now(UTC).year
        window = 20 if self._api_key else 10
        merged: dict[date, float | None] = {}
        for first in range(start_year, end_year + 1, window):
            for period, value in self._series_window(
                series_id, first, min(first + window - 1, end_year)
            ):
                merged[period] = value
        if not merged:
            raise BlsError(f"BLS returned no observations for {series_id}")
        return sorted(merged.items())

    def _series_window(
        self, series_id: str, start_year: int, end_year: int
    ) -> list[tuple[date, float | None]]:
        payload: dict[str, Any] = {
            "seriesid": [series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if self._api_key:
            payload["registrationkey"] = self._api_key

        body = self.post_json("/", payload, f"{series_id}-{start_year}-{end_year}")
        if body.get("status") != "REQUEST_SUCCEEDED":
            raise BlsError(f"BLS request for {series_id} failed: {self._message(body)}")
        results = body.get("Results", {})
        series_list = results.get("series") or []
        if not series_list:
            # An unknown id comes back as a success with no series and a message.
            raise BlsError(f"BLS has no series {series_id}: {self._message(body)}")
        # A series object holds only `seriesID` and `data`; it carries no status of its own.
        series_data = series_list[0]

        observations: list[tuple[date, float | None]] = []
        for item in series_data.get("data", []):
            period_date = _period_to_date(item["year"], item["period"])
            if period_date is None:
                continue
            value = item.get("value")
            try:
                value = float(value) if value not in (None, "", ".", " ", "-") else None
            except (TypeError, ValueError):
                value = None
            observations.append((date.fromisoformat(period_date), value))

        observations.sort()
        return observations

    def _message(self, body: dict) -> str:
        """BLS explains failures in a message array, which can echo the API key."""
        text = " ".join(str(m) for m in body.get("message") or []) or str(body.get("status"))
        if self._api_key:
            text = text.replace(self._api_key, "***")
        return text

    def post_json(self, path: str, payload: dict[str, Any], raw_name: str | None = None) -> dict:
        """POST a JSON body; BLS v2 uses POST for all data requests.

        Same retry policy as the base class's GET: network errors, 429 and 5xx are
        retried with backoff (BLS enforces 50 requests per 10 seconds).
        """
        content = json.dumps(payload).encode()
        for attempt in range(self._max_retries + 1):
            self._before_request()
            try:
                res = self._client.post(path, content=content)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    raise self.error(
                        f"{self.source} request failed: {type(exc).__name__}"
                    ) from None
                self._sleep(2**attempt)
                continue
            if res.status_code in RETRY_STATUSES and attempt < self._max_retries:
                self._sleep(retry_delay(res.headers.get("retry-after"), attempt))
                continue
            if res.status_code != 200:
                raise self._fail(res)
            if self._raw is not None and raw_name:
                self._raw.save(self.source, raw_name, res.content)
            try:
                return json.loads(res.content.decode("utf-8-sig"))
            except ValueError:
                raise self.error(f"{self.source} returned a response that is not JSON") from None
        raise self.error(f"{self.source} kept failing")  # pragma: no cover
