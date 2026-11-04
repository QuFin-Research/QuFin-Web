"""CFTC Public Reporting connector: Commitments of Traders, futures-only reports.

Legacy (commodities) and Traders in Financial Futures (financial contracts). Open data (Socrata
API), no key needed: https://publicreporting.cftc.gov/
"""

from collections.abc import Callable
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError
from app.data.cot_calendar import release_date
from app.stores.positioning import CotFinancialReport, CotReport

LEGACY_FUTURES_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
TFF_FUTURES_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
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

# Traders in Financial Futures columns, checked against the dataset on 5 Nov 2026. Some end in
# "_all" and some do not; that is how the CFTC names them.
TFF_FIELDS = {
    "open_interest": "open_interest_all",
    "dealer_long": "dealer_positions_long_all",
    "dealer_short": "dealer_positions_short_all",
    "dealer_spread": "dealer_positions_spread_all",
    "asset_mgr_long": "asset_mgr_positions_long",
    "asset_mgr_short": "asset_mgr_positions_short",
    "asset_mgr_spread": "asset_mgr_positions_spread",
    "lev_money_long": "lev_money_positions_long",
    "lev_money_short": "lev_money_positions_short",
    "lev_money_spread": "lev_money_positions_spread",
    "other_rept_long": "other_rept_positions_long",
    "other_rept_short": "other_rept_positions_short",
    "other_rept_spread": "other_rept_positions_spread",
    "nonrept_long": "nonrept_positions_long_all",
    "nonrept_short": "nonrept_positions_short_all",
}


class CftcError(SourceError):
    pass


def _common(row: dict) -> dict[str, Any]:
    report_date = date.fromisoformat(row["report_date_as_yyyy_mm_dd"][:10])
    return {
        "contract_code": row["cftc_contract_market_code"].strip(),
        "report_date": report_date,
        # Holidays, shutdowns and incidents delayed some releases: see app/data/cot_calendar.py.
        "release_date": release_date(report_date),
        "market_name": row.get("market_and_exchange_names", "").strip(),
    }


def parse_report(row: dict) -> CotReport:
    counts: dict[str, Any] = {
        name: int(float(row.get(column) or 0)) for name, column in FIELDS.items()
    }
    return CotReport(**_common(row), **counts)


def parse_financial_report(row: dict) -> CotFinancialReport:
    # A renamed column must fail loudly, not load as zero positions.
    missing = [column for column in TFF_FIELDS.values() if column not in row]
    if missing:
        raise CftcError(f"CFTC financial report row is missing {', '.join(missing)}")
    counts: dict[str, Any] = {
        name: int(float(row[column] or 0)) for name, column in TFF_FIELDS.items()
    }
    return CotFinancialReport(**_common(row), **counts)


class CftcClient(HttpSource):
    source = "cftc"
    error = CftcError

    def __init__(
        self, url: str = LEGACY_FUTURES_URL, tff_url: str = TFF_FUTURES_URL, **kwargs: Any
    ) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(**kwargs)
        self._url = url
        self._tff_url = tff_url

    def reports(self, contract_code: str, since: date) -> list[CotReport]:
        """Legacy weekly reports for one contract from `since`, oldest first."""
        return self._fetch(self._url, parse_report, contract_code, since, "legacy")

    def financial_reports(self, contract_code: str, since: date) -> list[CotFinancialReport]:
        """Traders in Financial Futures weekly reports from `since`, oldest first."""
        return self._fetch(self._tff_url, parse_financial_report, contract_code, since, "tff")

    def _fetch[T](
        self, url: str, parse: Callable[[dict], T], contract_code: str, since: date, kind: str
    ) -> list[T]:
        if not contract_code.isalnum():
            raise CftcError(f"Invalid contract code {contract_code!r}")
        where = (
            f"cftc_contract_market_code='{contract_code}' "
            f"AND report_date_as_yyyy_mm_dd >= '{since.isoformat()}'"
        )
        result: list[T] = []
        offset = 0
        while True:
            page = self.get_json(
                url,
                {
                    "$where": where,
                    "$order": "report_date_as_yyyy_mm_dd ASC",
                    "$limit": PAGE_LIMIT,
                    "$offset": offset,
                },
                f"{kind}-{contract_code}-{since.isoformat()}-{offset}",
            )
            result.extend(parse(row) for row in page)
            if len(page) < PAGE_LIMIT:
                return result
            offset += len(page)
