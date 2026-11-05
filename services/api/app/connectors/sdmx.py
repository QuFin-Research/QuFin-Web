"""Shared SDMX client: SDMX 2.1 REST data queries returning SDMX-JSON 1.0.

Statistical agencies (ECB, OECD, BIS, IMF, Eurostat) publish through the same SDMX standard, so
one client fetches and parses them all; each connector sets its base URL and source name. Built
on the connector framework (retries, raw zone, errors without URLs or keys).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.connectors.base import HttpSource, SourceError


class SdmxError(SourceError):
    pass


@dataclass(frozen=True)
class SdmxSeries:
    flow: str
    key: str
    title: str
    # Series attributes as published (e.g. UNIT, UNIT_MULT), by attribute id.
    attributes: dict[str, str]
    observations: list[tuple[date, float | None]]  # oldest first


def parse_period(period: str) -> date:
    """SDMX time periods as QuFin dates: a month, quarter or year by its first day."""
    if len(period) == 10:  # 2026-11-05
        return date.fromisoformat(period)
    if len(period) == 7 and period[4] == "-" and period[5] != "Q":  # 2026-10
        return date(int(period[:4]), int(period[5:]), 1)
    if "-Q" in period:  # 2026-Q3
        return date(int(period[:4]), 3 * int(period[-1]) - 2, 1)
    if len(period) == 4:  # 2026
        return date(int(period), 1, 1)
    raise SdmxError(f"Unsupported SDMX period {period!r}")


def _value(values: list[dict], index: Any) -> str | None:
    if index is None:
        return None
    item = values[int(index)]
    return str(item.get("name") or item.get("id"))


def parse_data_message(flow: str, key: str, body: dict) -> SdmxSeries:
    """The single series an SDMX-JSON data message returns for a fully specified key."""
    try:
        series = body["dataSets"][0]["series"]
        structure = body["structure"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SdmxError(f"{flow}/{key}: not an SDMX-JSON data message") from exc
    if len(series) != 1:
        raise SdmxError(f"{flow}/{key}: expected one series, got {len(series)}")
    [data] = series.values()
    periods = structure["dimensions"]["observation"][0]["values"]
    attribute_defs = structure.get("attributes", {}).get("series", [])
    attributes = {
        a["id"]: v
        for a, index in zip(attribute_defs, data.get("attributes", []), strict=False)
        if (v := _value(a.get("values", []), index)) is not None
    }
    observations = sorted(
        (parse_period(periods[int(i)]["id"]), None if obs[0] is None else float(obs[0]))
        for i, obs in data.get("observations", {}).items()
    )
    return SdmxSeries(flow, key, attributes.get("TITLE", key), attributes, observations)


class SdmxClient(HttpSource):
    error = SdmxError

    def describe_error(self, res: httpx.Response) -> str:
        try:
            body = res.json()
            return str(body.get("title") or body.get("detail") or res.reason_phrase)
        except ValueError:
            return res.reason_phrase

    def series(self, flow: str, key: str, start: date | None = None) -> SdmxSeries:
        """One series by dataflow and full key, e.g. ("HICP", "M.U2.N.000000.4D0.ANR")."""
        for part in (flow, key):
            if not part.replace(".", "").replace("_", "").isalnum():
                raise SdmxError(f"Invalid SDMX identifier {part!r}")
        params: dict[str, Any] = {"format": "jsondata"}
        if start is not None:
            params["startPeriod"] = start.isoformat()
        body = self.get_json(f"/data/{flow}/{key}", params, f"{flow}.{key}")
        return parse_data_message(flow, key, body)
