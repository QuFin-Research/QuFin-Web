"""CFTC Commitments of Traders reports (futures only), one row per contract per week.

Two reports, one table each: legacy (commodities) and Traders in Financial Futures (financial
contracts). A contract is stored from one report only (app/data/positioning_catalog.py).
Positions are as of Tuesday (`report_date`) but only public from the Friday release
(`release_date`). Point-in-time reads filter on the release date, so a backtest on a Wednesday
never sees that week's report early.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Date, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.data.cot_calendar import release_date
from app.data.positioning_catalog import CotContract, Report
from app.stores.db import Base


class CotReportRow(Base):
    __tablename__ = "cot_reports"

    contract_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    release_date: Mapped[date] = mapped_column(Date, index=True)
    market_name: Mapped[str] = mapped_column(String(128))
    open_interest: Mapped[int] = mapped_column(Integer)
    noncomm_long: Mapped[int] = mapped_column(Integer)
    noncomm_short: Mapped[int] = mapped_column(Integer)
    noncomm_spread: Mapped[int] = mapped_column(Integer)
    comm_long: Mapped[int] = mapped_column(Integer)
    comm_short: Mapped[int] = mapped_column(Integer)
    nonrept_long: Mapped[int] = mapped_column(Integer)
    nonrept_short: Mapped[int] = mapped_column(Integer)


class CotFinancialReportRow(Base):
    __tablename__ = "cot_financial_reports"

    contract_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    release_date: Mapped[date] = mapped_column(Date, index=True)
    market_name: Mapped[str] = mapped_column(String(128))
    open_interest: Mapped[int] = mapped_column(Integer)
    dealer_long: Mapped[int] = mapped_column(Integer)
    dealer_short: Mapped[int] = mapped_column(Integer)
    dealer_spread: Mapped[int] = mapped_column(Integer)
    asset_mgr_long: Mapped[int] = mapped_column(Integer)
    asset_mgr_short: Mapped[int] = mapped_column(Integer)
    asset_mgr_spread: Mapped[int] = mapped_column(Integer)
    lev_money_long: Mapped[int] = mapped_column(Integer)
    lev_money_short: Mapped[int] = mapped_column(Integer)
    lev_money_spread: Mapped[int] = mapped_column(Integer)
    other_rept_long: Mapped[int] = mapped_column(Integer)
    other_rept_short: Mapped[int] = mapped_column(Integer)
    other_rept_spread: Mapped[int] = mapped_column(Integer)
    nonrept_long: Mapped[int] = mapped_column(Integer)
    nonrept_short: Mapped[int] = mapped_column(Integer)


@dataclass(frozen=True)
class CotReport:
    contract_code: str
    report_date: date
    release_date: date
    market_name: str
    open_interest: int
    noncomm_long: int
    noncomm_short: int
    noncomm_spread: int
    comm_long: int
    comm_short: int
    nonrept_long: int
    nonrept_short: int


@dataclass(frozen=True)
class CotFinancialReport:
    contract_code: str
    report_date: date
    release_date: date
    market_name: str
    open_interest: int
    dealer_long: int
    dealer_short: int
    dealer_spread: int
    asset_mgr_long: int
    asset_mgr_short: int
    asset_mgr_spread: int
    lev_money_long: int
    lev_money_short: int
    lev_money_spread: int
    other_rept_long: int
    other_rept_short: int
    other_rept_spread: int
    nonrept_long: int
    nonrept_short: int


@dataclass(frozen=True)
class Positions:
    """One week of the group a contract's metrics follow, whichever report it comes from."""

    report_date: date
    release_date: date
    market_name: str
    open_interest: int
    long: int
    short: int
    # Asset managers (pension, mutual and insurance funds): financial futures only.
    asset_mgr_long: int | None = None
    asset_mgr_short: int | None = None


def _report(row: CotReportRow) -> CotReport:
    return CotReport(**{f: getattr(row, f) for f in CotReport.__dataclass_fields__})


def _financial(row: CotFinancialReportRow) -> CotFinancialReport:
    return CotFinancialReport(
        **{f: getattr(row, f) for f in CotFinancialReport.__dataclass_fields__}
    )


def legacy_positions(r: CotReport) -> Positions:
    return Positions(
        r.report_date,
        r.release_date,
        r.market_name,
        r.open_interest,
        r.noncomm_long,
        r.noncomm_short,
    )


def financial_positions(r: CotFinancialReport) -> Positions:
    return Positions(
        r.report_date,
        r.release_date,
        r.market_name,
        r.open_interest,
        r.lev_money_long,
        r.lev_money_short,
        r.asset_mgr_long,
        r.asset_mgr_short,
    )


_TABLES: dict[Report, type[CotReportRow] | type[CotFinancialReportRow]] = {
    "legacy": CotReportRow,
    "tff": CotFinancialReportRow,
}


class PositioningStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, reports: Iterable[CotReport | CotFinancialReport]) -> int:
        """Insert new weeks and overwrite re-published ones. Returns rows written."""
        count = 0
        for r in reports:
            if isinstance(r, CotFinancialReport):
                self.session.merge(CotFinancialReportRow(**r.__dict__))
            else:
                self.session.merge(CotReportRow(**r.__dict__))
            count += 1
        self.session.commit()
        return count

    def correct_release_dates(self) -> int:
        """Re-derive every stored release date from the CFTC calendar; returns rows changed.

        Rows ingested before a calendar fix (or before the calendar existed) would otherwise keep
        a too-early date, since a normal ingest only re-reads the latest weeks.
        """
        changed = 0
        rows: list[CotReportRow | CotFinancialReportRow] = [
            *self.session.scalars(select(CotReportRow)),
            *self.session.scalars(select(CotFinancialReportRow)),
        ]
        for row in rows:
            expected = release_date(row.report_date)
            if row.release_date != expected:
                row.release_date = expected
                changed += 1
        if changed:
            self.session.commit()
        return changed

    def latest_report_date(self, contract_code: str, report: Report = "legacy") -> date | None:
        table = _TABLES[report]
        return self.session.scalar(
            select(table.report_date)
            .where(table.contract_code == contract_code)
            .order_by(table.report_date.desc())
            .limit(1)
        )

    def history(self, contract_code: str, as_of: date | None = None) -> Sequence[CotReport]:
        """Legacy reports public by `as_of` (all when None), oldest first."""
        query = select(CotReportRow).where(CotReportRow.contract_code == contract_code)
        if as_of is not None:
            query = query.where(CotReportRow.release_date <= as_of)
        return [_report(r) for r in self.session.scalars(query.order_by(CotReportRow.report_date))]

    def financial_history(
        self, contract_code: str, as_of: date | None = None
    ) -> Sequence[CotFinancialReport]:
        """Traders in Financial Futures reports public by `as_of`, oldest first."""
        table = CotFinancialReportRow
        query = select(table).where(table.contract_code == contract_code)
        if as_of is not None:
            query = query.where(table.release_date <= as_of)
        return [_financial(r) for r in self.session.scalars(query.order_by(table.report_date))]

    def positions(self, contract: CotContract, as_of: date | None = None) -> list[Positions]:
        """The contract's weekly positions from its own report, public by `as_of`."""
        if contract.report == "tff":
            return [financial_positions(r) for r in self.financial_history(contract.code, as_of)]
        return [legacy_positions(r) for r in self.history(contract.code, as_of)]
