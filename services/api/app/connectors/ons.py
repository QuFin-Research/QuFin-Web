"""UK Office for National Statistics time series (keyless): https://www.ons.gov.uk

Each ONS time series page serves its whole history as JSON at `<page>/data`. The ONS publishes
the latest values only (no vintages), under the Open Government Licence v3.0. Its developer hub
(developer.ons.gov.uk/bots, read 13 Nov 2026) allows 120 requests per 10 seconds and 200 a minute,
asks bots to name themselves with a contact URL, and to honour `Retry-After` on a 429 (ignoring it
can bring a block of up to an hour). This client asks for one series every two seconds, which is
far below that, and stops for the run after a 403 or 429 (rule 28).

The `/data` time series endpoint is not described on the terms or developer pages (they document
a different, beta API); it is the page's own public data link, and is verified by the tests and
the release check, not by the supplier's documentation.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://www.ons.gov.uk"
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    )
}
_PATH = re.compile(r"^[a-z0-9/]+$")


class OnsError(SourceError):
    pass


@dataclass(frozen=True)
class OnsData:
    title: str
    unit: str
    observations: list[tuple[date, float]]
    next_release: str | None


def parse_period(label: str) -> date:
    """Read "2026 JUL" as 2026-07-01 and "2026 Q2" as 2026-04-01."""
    year, _, part = label.strip().partition(" ")
    if part.upper() in _MONTHS and year.isdigit():
        return date(int(year), _MONTHS[part.upper()], 1)
    if re.fullmatch(r"Q[1-4]", part.upper()) and year.isdigit():
        return date(int(year), 3 * int(part[1]) - 2, 1)
    raise OnsError(f"Unsupported ONS period {label!r}")


class OnsClient(HttpSource):
    source = "ons"
    min_interval = 2.0  # rule 28: the limits are 120 per 10 s; one series per two seconds
    error = OnsError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(self, path: str, frequency: str, start: date | None = None) -> OnsData:
        """One series by its page path, as `Monthly` or `Quarterly` observations from `start`."""
        if not _PATH.fullmatch(path):
            raise OnsError("Not an ONS time series path")
        body = self.get_json(f"/{path}/data", {}, path.rstrip("/").split("/")[-2])
        key = "months" if frequency == "Monthly" else "quarters"
        rows = body.get(key) or []
        if not rows:
            raise OnsError(f"ONS series {path} has no {key}")
        observations: list[tuple[date, float]] = []
        for row in rows:
            raw = str(row.get("value", "")).strip()
            if not raw:
                continue
            period = parse_period(str(row.get("date", "")))
            if start is not None and period < start:
                continue
            try:
                observations.append((period, float(raw)))
            except ValueError:
                raise OnsError(f"ONS series {path}: bad value {raw!r}") from None
        description = body.get("description") or {}
        return OnsData(
            title=str(description.get("title", "")),
            unit=str(description.get("unit", "")),
            observations=sorted(observations),
            next_release=description.get("nextRelease") or None,
        )
