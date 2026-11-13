"""Eurostat statistics API (JSON-stat, keyless): https://ec.europa.eu/eurostat

One request returns one series (every dimension pinned, one `geo`), so the response is a flat
list of monthly values. The reuse policy (copyright notice, read 13 Nov 2026) allows commercial
use of statistical data with the source acknowledged, except data for countries outside the EU,
EFTA and candidate countries: QuFin takes only euro area economies from it. The guidance pages
state no request rate limit, no key and no User-Agent rule; large extractions return an
asynchronous 413, which one series never reaches. This client asks for one series every two
seconds, names itself, and stops for the run after a 403 or 429 (rule 28).
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://ec.europa.eu"
PATH = "/eurostat/api/dissemination/statistics/1.0/data"
_DATASET = re.compile(r"^[a-z0-9_]+$")
_VALUE = re.compile(r"^[A-Za-z0-9_.-]+$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


class EurostatError(SourceError):
    pass


@dataclass(frozen=True)
class EurostatSeries:
    label: str
    observations: list[tuple[date, float]]


class EurostatClient(HttpSource):
    source = "eurostat"
    min_interval = 2.0  # rule 28: no stated limit; one series per two seconds
    error = EurostatError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        super().__init__(base_url, **kwargs)

    def series(
        self, dataset: str, filters: dict[str, str], start: date | None = None
    ) -> EurostatSeries:
        """Monthly observations of one fully specified series from `start`."""
        if not _DATASET.fullmatch(dataset) or not all(
            _VALUE.fullmatch(k) and _VALUE.fullmatch(v) for k, v in filters.items()
        ):
            raise EurostatError("Not a valid Eurostat dataset or filter")
        params: dict[str, str] = {"format": "JSON", "lang": "EN", **filters}
        if start is not None:
            params["sinceTimePeriod"] = f"{start.year}-{start.month:02d}"
        body = self.get_json(f"{PATH}/{dataset}", params, f"{dataset}-{filters.get('geo', '')}")
        return parse(body)


def parse(body: dict) -> EurostatSeries:
    """The values of a JSON-stat message with a single series, oldest first."""
    if "dimension" not in body or "value" not in body:
        raise EurostatError("Eurostat returned no data for that selection")
    ids, sizes = body["id"], body["size"]
    time_axis = ids.index("time")
    if any(sizes[i] != 1 for i in range(len(ids)) if i != time_axis):
        raise EurostatError("The selection holds more than one series")
    times = body["dimension"]["time"]["category"]["index"]
    by_position = {pos: label for label, pos in times.items()}
    observations = []
    values = body["value"]
    pairs = values.items() if isinstance(values, dict) else enumerate(values)
    for pos, value in pairs:
        pos = int(pos)
        if value is None:
            continue
        match = _MONTH.match(by_position[pos])
        if not match:
            raise EurostatError(f"Unsupported Eurostat period {by_position[pos]!r}")
        observations.append((date(int(match[1]), int(match[2]), 1), float(value)))
    if not observations:
        raise EurostatError("Eurostat returned no observations")
    return EurostatSeries(str(body.get("label", "")), sorted(observations))
