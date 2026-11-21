"""Reserve Bank of Australia statistical tables (CSV, keyless): https://www.rba.gov.au/statistics

`GET /statistics/tables/csv/<table>-data.csv`: a block of header rows (Title, Description,
Frequency, Type, Units, Source, Publication date, Series ID) and then one row per period with
dates as dd/mm/yyyy (verified 21 Nov 2026 for table D3, monetary aggregates). The header's
publication date is when the table was last published, which dates the newest period. The site
answers an unnamed client with "Access Denied", so the client names itself (QuFin's User-Agent).
Terms not read (rule 7). One table every two seconds (rule 28).
"""

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://www.rba.gov.au"
_TABLE = re.compile(r"^[a-z0-9-]{1,12}$")


class RbaError(SourceError):
    pass


def parse_table(text: str) -> tuple[date | None, dict[str, list[tuple[date, float]]]]:
    """The publication date and every series of one table, oldest first."""
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    ids = next((r for r in rows if r and r[0] == "Series ID"), None)
    if ids is None:
        raise RbaError("The RBA table has no Series ID row")
    published = next((r for r in rows if r and r[0] == "Publication date"), None)
    published_on = None
    if published and len(published) > 1:
        try:
            published_on = datetime.strptime(published[1], "%d-%b-%Y").date()
        except ValueError:
            published_on = None
    series: dict[str, list[tuple[date, float]]] = {sid: [] for sid in ids[1:] if sid}
    for row in rows[rows.index(ids) + 1 :]:
        if not row or not row[0]:
            continue
        try:
            period = datetime.strptime(row[0], "%d/%m/%Y").date()
        except ValueError:
            continue  # a note or a blank line, not an observation
        for sid, raw in zip(ids[1:], row[1:], strict=False):
            if sid and raw.strip():
                try:
                    series[sid].append((period, float(raw)))
                except ValueError:
                    continue
    return published_on, series


class RbaClient(HttpSource):
    source = "rba"
    min_interval = 2.0  # rule 28: no stated rate; one table every two seconds
    error = RbaError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(
        self, table: str, series_id: str, start: date | None = None
    ) -> tuple[date | None, list[tuple[date, float]]]:
        """One series of a table from `start` and the table's publication date."""
        if not _TABLE.fullmatch(table):
            raise RbaError("Not a valid RBA table name")
        text = self.get(f"/statistics/tables/csv/{table}-data.csv", {}, table).text
        published, tables = parse_table(text)
        if series_id not in tables:
            raise RbaError(f"Table {table} has no series {series_id}")
        found = [(p, v) for p, v in tables[series_id] if start is None or p >= start]
        if not found:
            raise RbaError(f"Table {table} has no observations of {series_id}")
        return published, found
