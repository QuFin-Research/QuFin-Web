"""World Bank Indicators API v2 (keyless): https://api.worldbank.org

Annual indicators for many countries at once: the country codes join with ";". The developer
pages (read 13 Nov 2026) say no key is needed and give no request rate limit, only that use must
not "exceed reasonable request volume"; they state no maximum for `per_page` or for the number of
countries. The API answered slowly or with a 502 and a read timeout on 13 Nov 2026 when asked for 50
countries and 37 years at once, so this client asks for at most ten countries per request, waits
three seconds between requests, allows four minutes per response, retries with backoff, and stops
for the run after a 403 or 429 (rule 28).

The terms of use page (worldbank.org/en/about/legal/terms-of-use-for-datasets) allows
non-commercial use and requires attribution to "The World Bank Group"; it points to dataset-specific
terms it does not itself contain, so the licence for a commercial product is recorded as to be
confirmed in `docs/licence-register.md`.
"""

import re
from collections.abc import Sequence
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://api.worldbank.org"
MAX_COUNTRIES_PER_REQUEST = 10
_CODE = re.compile(r"^[A-Z0-9.]+$")
_ISO3 = re.compile(r"^[A-Z]{3}$")


class WorldBankError(SourceError):
    pass


class WorldBankClient(HttpSource):
    source = "worldbank"
    min_interval = 3.0  # rule 28: no stated limit, and the API was slow on 13 Nov 2026
    error = WorldBankError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 240.0)
        kwargs.setdefault("max_retries", 4)
        super().__init__(base_url, **kwargs)

    def indicator(
        self, code: str, countries: Sequence[str], start: date | None = None
    ) -> dict[str, list[tuple[date, float]]]:
        """Annual values of one indicator for up to ten countries, by ISO3 code (January 1)."""
        if not _CODE.fullmatch(code) or not all(_ISO3.fullmatch(c) for c in countries):
            raise WorldBankError("Not a valid World Bank indicator or country code")
        if not 0 < len(countries) <= MAX_COUNTRIES_PER_REQUEST:
            raise WorldBankError(f"Ask for 1 to {MAX_COUNTRIES_PER_REQUEST} countries at a time")
        first = start.year if start else 1960
        result: dict[str, list[tuple[date, float]]] = {c: [] for c in countries}
        page = 1
        while True:
            body = self.get_json(
                f"/v2/country/{';'.join(countries)}/indicator/{code}",
                {
                    "format": "json",
                    "date": f"{first}:{date.today().year}",
                    "per_page": 1000,
                    "page": page,
                },
                f"{code}-{countries[0]}-{page}",
            )
            if not isinstance(body, list) or len(body) < 2:
                raise WorldBankError(f"World Bank returned an unexpected message for {code}")
            meta, rows = body[0], body[1] or []
            for row in rows:
                if row.get("value") is None:
                    continue
                iso3 = row.get("countryiso3code") or (row.get("country") or {}).get("id")
                if iso3 in result:
                    result[iso3].append((date(int(row["date"]), 1, 1), float(row["value"])))
            if page >= int(meta.get("pages", 1)):
                break
            page += 1
        return {c: sorted(v) for c, v in result.items()}
