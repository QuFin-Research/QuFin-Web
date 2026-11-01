"""Shared plumbing for every connector (backlog P1-06).

A connector subclasses `HttpSource` and implements only what is specific to its source: which
endpoints to call and how to parse them. The base gives every source the same behaviour:

- retries with exponential backoff on network errors, 429 and 5xx (honouring `Retry-After`);
- the operating system's certificate store (`truststore`), so TLS-inspecting proxies trusted on
  the machine work;
- every response body saved to the raw zone before it is parsed, when one is configured;
- errors that never echo request URLs, so API keys in query strings cannot leak into logs.
"""

import ssl
import time
from collections.abc import Callable
from typing import Any

import httpx
import truststore

from app.stores.raw_zone import RawZone

RETRY_STATUSES = {429, 500, 502, 503, 504}


class SourceError(Exception):
    pass


class HttpSource:
    source = "source"  # raw-zone folder and error prefix; set by each connector
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
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )
        self._max_retries = max_retries
        self._sleep = sleep
        self._raw = raw

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def describe_error(self, res: httpx.Response) -> str:
        """The source's own explanation of a failed request, without the URL."""
        return res.text[:200] or res.reason_phrase

    def get(self, path: str, params: dict[str, Any], raw_name: str | None = None) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
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
                self._sleep(float(res.headers.get("retry-after", 2**attempt)))
                continue
            if res.status_code != 200:
                raise self.error(
                    f"{self.source} returned {res.status_code}: {self.describe_error(res)}"
                )
            if self._raw is not None and raw_name:
                self._raw.save(self.source, raw_name, res.content)
            return res
        raise self.error(f"{self.source} kept failing")  # pragma: no cover

    def get_json(self, path: str, params: dict[str, Any], raw_name: str | None = None) -> Any:
        return self.get(path, params, raw_name).json()
