"""Singapore Department of Statistics, Table Builder API (keyless).

`GET https://tablebuilder.singstat.gov.sg/api/table/tabledata/<table id>` returns
`{"Data": {"row": [{"seriesNo", "rowText", "uoM", "columns": [{"key": "2026 3Q", "value": "2"}]}]}}`
(verified 13 Nov 2026 for table M182342, "Unemployment Rate (End Of Period), Quarterly,
Seasonally Adjusted", whose row 1 is "Total Unemployment Rate, (SA)", 1992 1Q to 2026 3Q). The
search endpoint `/api/table/resourceid?keyword=...` found the table. The supplier's terms were not
read (`country_sources.py` says so), so the series stays unscored and flagged until they are.
This client asks for one table every two seconds, names itself and stops for the run after a 403
or 429 (rule 28).
"""

import re
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://tablebuilder.singstat.gov.sg"
_TABLE = re.compile(r"^[A-Z][0-9]{4,8}$")
_QUARTER = re.compile(r"^(\d{4}) ([1-4])Q$")


class SingStatError(SourceError):
    pass


def parse_quarter(key: str) -> date:
    """Read "2026 3Q" as 2026-07-01."""
    match = _QUARTER.match(key.strip())
    if not match:
        raise SingStatError(f"Unsupported SingStat period {key!r}")
    return date(int(match[1]), 3 * int(match[2]) - 2, 1)


class SingStatClient(HttpSource):
    source = "singstat"
    min_interval = 2.0  # rule 28: no stated rate; one table every two seconds
    error = SingStatError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(
        self, table_id: str, series_no: str, start: date | None = None
    ) -> list[tuple[date, float]]:
        """One row of a quarterly table as observations from `start`, oldest first."""
        if not _TABLE.fullmatch(table_id):
            raise SingStatError("Not a valid SingStat table id")
        body = self.get_json(f"/api/table/tabledata/{table_id}", {}, table_id)
        rows = (body.get("Data") or {}).get("row") or []
        row = next((r for r in rows if str(r.get("seriesNo")) == series_no), None)
        if row is None:
            raise SingStatError(f"Table {table_id} has no series {series_no}")
        observations = []
        for column in row.get("columns", []):
            raw = str(column.get("value", "")).strip()
            if not raw:
                continue
            period = parse_quarter(str(column.get("key", "")))
            if start is not None and period < start:
                continue
            try:
                observations.append((period, float(raw)))
            except ValueError:
                raise SingStatError(f"Table {table_id}: bad value {raw!r}") from None
        if not observations:
            raise SingStatError(f"Table {table_id} series {series_no} has no observations")
        return sorted(observations)
