"""Bank of Canada Valet API (keyless): https://www.bankofcanada.ca/valet

`GET /valet/observations/<series>/json?start_date=YYYY-MM-DD` returns
`{"observations": [{"d": "2026-10-01", "<SERIES>": {"v": "2.50"}}]}` (verified 21 Nov 2026 for
V122530, the Bank Rate). The response names the Bank's terms page; the terms were not read, so a
series from here stays unscored and flagged until they are (`country_sources.py`, rule 7). One
series every second, a descriptive User-Agent, and a stop for the run after a 403 or 429 (rule 28).
"""

import re
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://www.bankofcanada.ca"
_SERIES = re.compile(r"^[A-Za-z0-9_.-]{2,40}$")


class BankOfCanadaError(SourceError):
    pass


class BankOfCanadaClient(HttpSource):
    source = "bankofcanada"
    min_interval = 1.0  # rule 28: no stated rate; one series a second
    error = BankOfCanadaError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(self, series_id: str, start: date | None = None) -> list[tuple[date, float]]:
        """The observations of one Valet series from `start`, oldest first."""
        if not _SERIES.fullmatch(series_id):
            raise BankOfCanadaError("Not a valid Valet series id")
        params = {"start_date": start.isoformat()} if start else {}
        body = self.get_json(f"/valet/observations/{series_id}/json", params, series_id)
        observations = []
        for item in body.get("observations") or []:
            raw = (item.get(series_id) or {}).get("v")
            if raw in (None, ""):
                continue
            try:
                observations.append((date.fromisoformat(item["d"]), float(raw)))
            except (KeyError, ValueError):
                raise BankOfCanadaError(f"Unreadable Valet observation for {series_id}") from None
        if not observations:
            raise BankOfCanadaError(f"The Valet API returned no observations for {series_id}")
        return sorted(observations)
