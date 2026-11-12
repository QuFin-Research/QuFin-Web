"""BIS Data Portal connector (SDMX REST API v2, keyless): https://data.bis.org

Policy rates, effective exchange rates and credit-to-GDP for economies FRED carries only late.
Use is free provided the BIS is cited as the source (https://data.bis.org/help/legal).

One request returns many economies at once (the key joins areas with "+"); each comes back as a
series whose REF_AREA dimension names it. The v2 API answers SDMX-JSON only when asked for it in
the Accept header, and the terms ask users to use the latest API version.
"""

import hashlib
from datetime import date
from typing import Any

from app.connectors.sdmx import SdmxClient, SdmxSeries, _check_identifier, parse_all

BASE_URL = "https://stats.bis.org/api/v2"
DATAFLOW_VERSION = "1.0"


class BisClient(SdmxClient):
    source = "bis"

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        kwargs.setdefault("headers", {"Accept": "application/vnd.sdmx.data+json;version=1.0.0"})
        super().__init__(base_url, **kwargs)

    def _data(self, flow: str, key: str, start: date | None) -> dict:
        _check_identifier(flow, "_")
        _check_identifier(key, "._+")
        params = {"startPeriod": start.isoformat()} if start is not None else {}
        # The key can hold dozens of areas: a short hash keeps the raw-zone file name usable.
        name = f"{flow}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"
        path = f"/data/dataflow/BIS/{flow}/{DATAFLOW_VERSION}/{key}"
        return self.get_json(path, params, name)

    def many(self, flow: str, key: str, start: date | None = None) -> list[SdmxSeries]:
        """Every series the key selects (one per economy), each with its dimensions."""
        return parse_all(flow, key, self._data(flow, key, start))
