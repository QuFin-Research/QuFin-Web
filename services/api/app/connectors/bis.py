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
    min_interval = 1.0  # rule 28: no published limit; one request per measure

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        kwargs.setdefault("headers", {"Accept": "application/vnd.sdmx.data+json;version=1.0.0"})
        super().__init__(base_url, **kwargs)

    def _data(self, flow: str, key: str, start: date | None) -> dict:
        return self._fetch(flow, key, start, DATAFLOW_VERSION)

    def _fetch(self, flow: str, key: str, start: date | None, version: str) -> dict:
        _check_identifier(flow, "_")
        _check_identifier(key, "._+*")
        _check_identifier(version, ".")
        params = {"startPeriod": start.isoformat()} if start is not None else {}
        # The key can hold dozens of areas: a short hash keeps the raw-zone file name usable.
        name = f"{flow}-{hashlib.sha256(f'{version}/{key}'.encode()).hexdigest()[:8]}"
        path = f"/data/dataflow/BIS/{flow}/{version}/{key}"
        return self.get_json(path, params, name)

    def many(
        self, flow: str, key: str, start: date | None = None, version: str = DATAFLOW_VERSION
    ) -> list[SdmxSeries]:
        """Every series the key selects (one per economy), each with its dimensions.

        `version` is the dataflow's own: most are 1.0, total credit (`WS_TC`) is 2.0.
        """
        return parse_all(flow, key, self._fetch(flow, key, start, version))
