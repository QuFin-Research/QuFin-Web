"""Banco Central do Brasil, Time Series Management System (SGS) API (keyless).

`GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json&dataInicial=dd/mm/yyyy
&dataFinal=dd/mm/yyyy` returns `[{"data": "dd/mm/yyyy", "valor": "..."}]`. The service limits a
request to ten years of data, so a longer history is fetched in windows of at most ten years
(verified 13 Nov 2026 for series 24369 and 22707 over 2023 to 2026, and 22707 back to 1990;
the ten-year rule is the supplier's own guidance as recalled, not re-read today).
No key and no stated request rate; this client asks for one window every two seconds, names itself
and stops for the run after a 403 or 429 (rule 28).
"""

from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://api.bcb.gov.br"
WINDOW_YEARS = 10


class BcbError(SourceError):
    pass


def windows(start: date, end: date) -> list[tuple[date, date]]:
    """Consecutive spans of at most ten years that cover `start` to `end`."""
    spans = []
    first = start
    while first <= end:
        last = min(date(first.year + WINDOW_YEARS, first.month, 1) - date.resolution, end)
        spans.append((first, last))
        first = last + date.resolution
    return spans


class BcbClient(HttpSource):
    source = "bcb"
    min_interval = 2.0  # rule 28: no stated rate; one window every two seconds
    error = BcbError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)

    def series(self, code: int, start: date, end: date | None = None) -> list[tuple[date, float]]:
        """Every observation of one SGS series from `start` to `end` (today), oldest first."""
        end = end or date.today()
        if code <= 0:
            raise BcbError("Not a valid SGS series code")
        observations: dict[date, float] = {}
        for first, last in windows(start, end):
            try:
                body = self.get_json(
                    f"/dados/serie/bcdata.sgs.{int(code)}/dados",
                    {
                        "formato": "json",
                        "dataInicial": first.strftime("%d/%m/%Y"),
                        "dataFinal": last.strftime("%d/%m/%Y"),
                    },
                    f"sgs-{code}-{first.year}",
                )
            except BcbError as exc:
                # A window before the series began answers 404 "Value(s) not found": not an
                # error, the series simply has nothing there (seen 13 Nov 2026 for series 24369,
                # which starts in 2012). Any other failure still stops the load.
                if "returned 404" in str(exc) and "not found" in str(exc).lower():
                    continue
                raise
            if not isinstance(body, list):
                raise BcbError(f"BCB returned an unexpected message for series {code}")
            for row in body:
                raw = str(row.get("valor", "")).strip()
                if not raw:
                    continue
                day, month, year = str(row["data"]).split("/")
                try:
                    observations[date(int(year), int(month), int(day))] = float(raw)
                except ValueError:
                    raise BcbError(f"BCB series {code}: bad value {raw!r}") from None
        if not observations:
            raise BcbError(f"BCB series {code} has no observations from {start}")
        return sorted(observations.items())
