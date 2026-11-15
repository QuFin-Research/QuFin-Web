"""Shared plumbing for every connector (backlog P1-06).

A connector subclasses `HttpSource` and implements only what is specific to its source: which
endpoints to call and how to parse them. The base gives every source the same behaviour:

- retries with exponential backoff on network errors, 429 and 5xx (honouring `Retry-After`);
- the operating system's certificate store (`truststore`), so TLS-inspecting proxies trusted on
  the machine work;
- a descriptive User-Agent, a minimum gap between requests (`min_interval`, set per source from
  its published limits) and a stop after the supplier refuses (403 or 429): rule 28;
- every response body saved to the raw zone before it is parsed, when one is configured;
- errors that never echo request URLs, so API keys in query strings cannot leak into logs.
"""

import json
import ssl
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import truststore

from app.stores.raw_zone import RawZone

RETRY_STATUSES = {429, 500, 502, 503, 504}
# The supplier saying no: asking again risks a ban, so the client stops for the rest of the run.
REFUSED_STATUSES = {403, 429}
USER_AGENT = "QuFin-data-client/1.0 (+https://github.com/QuFin-Research/QuFin-Web)"
MAX_RETRY_WAIT = 120.0


def retry_delay(retry_after: str | None, attempt: int) -> float:
    """Seconds to wait before a retry: `Retry-After` (seconds or an HTTP date), else backoff."""
    backoff = float(2**attempt)
    if retry_after is None:
        return backoff
    try:
        wait = float(retry_after)
    except ValueError:
        try:
            when = parsedate_to_datetime(retry_after)
        except (TypeError, ValueError):
            return backoff
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        wait = (when - datetime.now(UTC)).total_seconds()
    return min(max(wait, 0.0), MAX_RETRY_WAIT)


class SourceError(Exception):
    pass


class HttpSource:
    source = "source"  # raw-zone folder and error prefix; set by each connector
    min_interval = 0.0  # seconds between requests, set per connector from its supplier's limits
    error: type[SourceError] = SourceError

    def __init__(
        self,
        base_url: str = "",
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        raw: RawZone | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        min_interval: float | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": USER_AGENT, **(headers or {})},
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )
        self._max_retries = max_retries
        self._sleep = sleep
        self._raw = raw
        self._min_interval = self.min_interval if min_interval is None else min_interval
        self._last_request: float | None = None
        self._refused = False

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def describe_error(self, res: httpx.Response) -> str:
        """The source's own explanation of a failed request, without the URL."""
        return res.text[:200] or res.reason_phrase

    def _before_request(self) -> None:
        """Keep the minimum gap between requests; never ask again once the supplier has refused."""
        if self._refused:
            raise self.error(f"{self.source} refused an earlier request; not asking again this run")
        if self._min_interval and self._last_request is not None:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = time.monotonic()

    def _fail(self, res: httpx.Response) -> SourceError:
        if res.status_code in REFUSED_STATUSES:
            self._refused = True
        return self.error(f"{self.source} returned {res.status_code}: {self.describe_error(res)}")

    def get(self, path: str, params: dict[str, Any], raw_name: str | None = None) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            self._before_request()
            try:
                res = self._client.get(path, params=params)
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
            return res
        raise self.error(f"{self.source} kept failing")  # pragma: no cover

    def get_json(self, path: str, params: dict[str, Any], raw_name: str | None = None) -> Any:
        res = self.get(path, params, raw_name)
        try:
            # utf-8-sig: some sources (the IMF) start their JSON with a byte-order mark.
            return json.loads(res.content.decode("utf-8-sig"))
        except ValueError:
            raise self.error(f"{self.source} returned a response that is not JSON") from None
