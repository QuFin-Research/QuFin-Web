"""Bank of England Statistical Interactive Database (CSV, keyless).

`GET /boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&SeriesCodes=<code>&Datefrom=<dd/Mon/yyyy>
&Dateto=now&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N` returns `DATE,<CODE>` and one row per period with
dates as "31 Jan 2026" (verified 21 Nov 2026 for LPMVWYR, M4 outstanding). A monthly series is
dated by the first of its month. Terms not read (rule 7). One series every two seconds (rule 28).
"""

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://www.bankofengland.co.uk"
_CODE = re.compile(r"^[A-Z0-9]{4,12}$")


class BoeError(SourceError):
    pass


def parse_csv(text: str, code: str) -> list[tuple[date, float]]:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows or [c.strip() for c in rows[0][:2]] != ["DATE", code]:
        raise BoeError(f"The Bank of England returned no table for {code}")
    observations = []
    for row in rows[1:]:
        if len(row) < 2 or not row[1].strip():
            continue
        try:
            when = datetime.strptime(row[0].strip(), "%d %b %Y").date()
            observations.append((date(when.year, when.month, 1), float(row[1])))
        except ValueError:
            raise BoeError(f"Unreadable Bank of England row for {code}") from None
    if not observations:
        raise BoeError(f"The Bank of England returned no observations for {code}")
    return sorted(observations)


class BoeClient(HttpSource):
    source = "boe"
    min_interval = 2.0  # rule 28: no stated rate; one series every two seconds
    error = BoeError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(self, code: str, start: date | None = None) -> list[tuple[date, float]]:
        """One IADB series from `start`, oldest first."""
        if not _CODE.fullmatch(code):
            raise BoeError("Not a valid Bank of England series code")
        first = start or date(1990, 1, 1)
        params = {
            "csv.x": "yes",
            "SeriesCodes": code,
            "Datefrom": first.strftime("%d/%b/%Y"),
            "Dateto": "now",
            "CSVF": "TN",
            "UsingCodes": "Y",
            "VPD": "Y",
            "VFD": "N",
        }
        text = self.get("/boeapps/database/_iadb-fromshowcolumns.asp", params, code).text
        return parse_csv(text, code)
