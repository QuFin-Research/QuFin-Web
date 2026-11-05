"""Treasury Fiscal Data connector (Bureau of the Fiscal Service), keyless.

Used only for what FRED does not carry (rule 17): the daily Debt to the Penny, the monthly
average interest rates on Treasury securities and the monthly interest expense on the public
debt. The API serves current values only, with no vintages.
https://fiscaldata.treasury.gov/api-documentation/
"""

from collections import defaultdict
from datetime import date
from typing import Any

from app.connectors.base import HttpSource, SourceError

BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
PAGE_SIZE = 10000

DEBT_TO_PENNY = "/v2/accounting/od/debt_to_penny"
AVG_INTEREST_RATES = "/v2/accounting/od/avg_interest_rates"
INTEREST_EXPENSE = "/v2/accounting/od/interest_expense"


class TreasuryError(SourceError):
    pass


def _month(record_date: str) -> date:
    """Monthly records are dated at month end; QuFin dates months by their first day."""
    d = date.fromisoformat(record_date)
    return d.replace(day=1)


class TreasuryClient(HttpSource):
    source = "treasury"
    error = TreasuryError

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        super().__init__(base_url, **kwargs)

    def describe_error(self, res: Any) -> str:
        try:
            body = res.json()
            return str(body.get("message") or body.get("error") or res.reason_phrase)
        except ValueError:
            return res.reason_phrase

    def _records(self, path: str, start: date, filters: str = "") -> list[dict]:
        where = f"record_date:gte:{start.isoformat()}" + (f",{filters}" if filters else "")
        rows: list[dict] = []
        page = 1
        while True:
            body = self.get_json(
                path,
                {
                    "filter": where,
                    "sort": "record_date",
                    "page[size]": PAGE_SIZE,
                    "page[number]": page,
                },
                f"{path.rsplit('/', 1)[-1]}-{start.isoformat()}-{page}",
            )
            rows.extend(body.get("data") or [])
            if page >= int((body.get("meta") or {}).get("total-pages") or 1):
                return rows
            page += 1

    def total_public_debt(self, start: date) -> list[tuple[date, float]]:
        """Total public debt outstanding in dollars, each business day."""
        rows = self._records(DEBT_TO_PENNY, start)
        return [
            (date.fromisoformat(r["record_date"]), float(r["tot_pub_debt_out_amt"])) for r in rows
        ]

    def average_interest_rate(self, security: str, start: date) -> list[tuple[date, float]]:
        """Average interest rate (percent) on one security class, e.g. "Total Marketable"."""
        if not security.replace(" ", "").replace("-", "").isalnum():
            raise TreasuryError(f"Invalid security description {security!r}")
        rows = self._records(AVG_INTEREST_RATES, start, f"security_desc:eq:{security}")
        if not rows:
            raise TreasuryError(f"Treasury has no average interest rate for {security!r}")
        return [(_month(r["record_date"]), float(r["avg_interest_rate_amt"])) for r in rows]

    def interest_expense(self, start: date) -> list[tuple[date, float]]:
        """Monthly interest expense on the public debt in dollars: the sum of every line.

        The dataset has no total row; its lines sum to Treasury's published totals (FY2024:
        $1,133.0 billion, checked 5 Nov 2026).
        """
        totals: dict[date, float] = defaultdict(float)
        for r in self._records(INTEREST_EXPENSE, start):
            totals[_month(r["record_date"])] += float(r["month_expense_amt"] or 0)
        return sorted(totals.items())
