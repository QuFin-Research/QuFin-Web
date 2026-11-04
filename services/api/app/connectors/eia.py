"""EIA API v2 connector for the Weekly Petroleum Status Report (oil inventories, supply, demand).

Used only for what FRED does not carry (rule 17): the weekly petroleum series. Prices stay on FRED
(DCOILWTICO, DCOILBRENTEU), which republishes the same EIA spot prices with vintages.

The `/v2/seriesid/` endpoint returns a series' full history newest first and ignores sort and
start parameters, so the client pages through everything and filters and sorts locally. The API
key travels as a query parameter; the base class keeps it out of errors and the raw zone.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.connectors.base import HttpSource, SourceError

PAGE_LIMIT = 5000

# EIA unit codes to the units shown to users.
UNITS = {
    "MBBL": "Thousand Barrels",
    "MBBL/D": "Thousand Barrels per Day",
    "%": "Percent",
}


class EiaError(SourceError):
    pass


@dataclass(frozen=True)
class EiaSeries:
    id: str
    title: str
    units: str
    observations: list[tuple[date, float | None]]  # oldest first


class EiaClient(HttpSource):
    source = "eia"
    error = EiaError

    def __init__(self, api_key: str, base_url: str = "https://api.eia.gov/v2", **kwargs: Any):
        super().__init__(base_url, **kwargs)
        self._api_key = api_key

    def describe_error(self, res: httpx.Response) -> str:
        try:
            return str(res.json().get("error", {}).get("message", "")) or res.reason_phrase
        except ValueError:
            return res.reason_phrase

    def weekly_petroleum(self, series_id: str, start: date | None = None) -> EiaSeries:
        """One WPSR series (e.g. "WCESTUS1"), all weeks from `start`, oldest first."""
        if not series_id.replace("_", "").isalnum():
            raise EiaError(f"Invalid EIA series id {series_id!r}")
        rows: list[dict] = []
        total = None
        while total is None or len(rows) < total:
            body = self.get_json(
                f"/seriesid/PET.{series_id}.W",
                {"api_key": self._api_key, "length": PAGE_LIMIT, "offset": len(rows)},
                f"{series_id}-{len(rows)}",
            )
            response = body.get("response") or {}
            page = response.get("data") or []
            total = int(response.get("total") or 0)
            if not page:
                break
            rows.extend(page)
        if not rows:
            raise EiaError(f"EIA has no data for {series_id}")
        observations = sorted(
            (
                (date.fromisoformat(r["period"]), None if r["value"] is None else float(r["value"]))
                for r in rows
            ),
            key=lambda o: o[0],
        )
        if start is not None:
            observations = [o for o in observations if o[0] >= start]
        first = rows[0]
        units = str(first.get("units") or "")
        return EiaSeries(
            id=series_id,
            title=str(first.get("series-description") or series_id),
            units=UNITS.get(units, units),
            observations=observations,
        )
