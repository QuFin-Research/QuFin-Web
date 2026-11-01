"""CFTC Public Reporting connector: Commitments of Traders, legacy futures-only report.

Open data (Socrata API), no key needed: https://publicreporting.cftc.gov/
"""

from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError
from app.data.cot_calendar import release_date
from app.stores.positioning import CotReport

LEGACY_FUTURES_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
PAGE_LIMIT = 5000

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


class CftcError(SourceError):
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


class CftcClient(HttpSource):
    source = "cftc"
    error = CftcError

    def __init__(self, url: str = LEGACY_FUTURES_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(**kwargs)
        self._url = url

    def _get(self, params: dict[str, str | int], raw_name: str | None = None) -> list[dict]:
        return self.get_json(self._url, params, raw_name)

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
                },
                f"{contract_code}-{since.isoformat()}-{offset}",
            )
            result.extend(parse_report(row) for row in page)
            if len(page) < PAGE_LIMIT:
                return result
            offset += len(page)
