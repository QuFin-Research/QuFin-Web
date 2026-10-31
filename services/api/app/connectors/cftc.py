"""CFTC Public Reporting connector: Commitments of Traders, legacy futures-only report.

Open data (Socrata API), no key needed: https://publicreporting.cftc.gov/
"""

import ssl
import time
from collections.abc import Callable
from datetime import date

import httpx
import truststore

from app.data.cot_calendar import release_date
from app.stores.positioning import CotReport

LEGACY_FUTURES_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
PAGE_LIMIT = 5000
RETRY_STATUSES = {429, 500, 502, 503, 504}

FIELDS = {
    "open_interest": "open_interest_all",
    "noncomm_long": "noncomm_positions_long_all",
    "noncomm_short": "noncomm_positions_short_all",
    "noncomm_spread": "noncomm_postions_spread_all",  # sic: the CFTC column name
    "comm_long": "comm_positions_long_all",
    "comm_short": "comm_positions_short_all",
    "nonrept_long": "nonrept_positions_long_all",
    "nonrept_short": "nonrept_positions_short_all",
}


class CftcError(Exception):
    pass


def parse_report(row: dict) -> CotReport:
    report_date = date.fromisoformat(row["report_date_as_yyyy_mm_dd"][:10])
    return CotReport(
        contract_code=row["cftc_contract_market_code"].strip(),
        report_date=report_date,
        # Holidays, shutdowns and incidents delayed some releases: see app/data/cot_calendar.py.
        release_date=release_date(report_date),
        market_name=row.get("market_and_exchange_names", "").strip(),
        **{name: int(float(row.get(column) or 0)) for name, column in FIELDS.items()},
    )


class CftcClient:
    def __init__(
        self,
        url: str = LEGACY_FUTURES_URL,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = url
        self._client = httpx.Client(
            timeout=60.0,
            transport=transport,
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )
        self._max_retries = max_retries
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CftcClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _get(self, params: dict[str, str | int]) -> list[dict]:
        for attempt in range(self._max_retries + 1):
            try:
                res = self._client.get(self._url, params=params)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    raise CftcError(f"CFTC request failed: {type(exc).__name__}") from None
                self._sleep(2**attempt)
                continue
            if res.status_code in RETRY_STATUSES and attempt < self._max_retries:
                self._sleep(2**attempt)
                continue
            if res.status_code != 200:
                raise CftcError(f"CFTC returned {res.status_code}: {res.text[:200]}")
            return res.json()
        raise CftcError("CFTC kept failing")  # pragma: no cover

    def reports(self, contract_code: str, since: date) -> list[CotReport]:
        """Weekly reports for one contract from `since`, oldest first."""
        if not contract_code.isalnum():
            raise CftcError(f"Invalid contract code {contract_code!r}")
        where = (
            f"cftc_contract_market_code='{contract_code}' "
            f"AND report_date_as_yyyy_mm_dd >= '{since.isoformat()}'"
        )
        result: list[CotReport] = []
        offset = 0
        while True:
            page = self._get(
                {
                    "$where": where,
                    "$order": "report_date_as_yyyy_mm_dd ASC",
                    "$limit": PAGE_LIMIT,
                    "$offset": offset,
                }
            )
            result.extend(parse_report(row) for row in page)
            if len(page) < PAGE_LIMIT:
                return result
            offset += len(page)
