"""CFTC Commitments of Traders reports (legacy, futures only), one row per contract per week.

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


def _report(row: CotReportRow) -> CotReport:
    return CotReport(**{f: getattr(row, f) for f in CotReport.__dataclass_fields__})


class PositioningStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, reports: Iterable[CotReport]) -> int:
        """Insert new weeks and overwrite re-published ones. Returns rows written."""
        count = 0
        for r in reports:
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
        for row in self.session.scalars(select(CotReportRow)):
            expected = release_date(row.report_date)
            if row.release_date != expected:
                row.release_date = expected
                changed += 1
        if changed:
            self.session.commit()
        return changed

    def latest_report_date(self, contract_code: str) -> date | None:
        return self.session.scalar(
            select(CotReportRow.report_date)
            .where(CotReportRow.contract_code == contract_code)
            .order_by(CotReportRow.report_date.desc())
            .limit(1)
        )

    def history(self, contract_code: str, as_of: date | None = None) -> Sequence[CotReport]:
        """Reports public by `as_of` (all when None), oldest first."""
        query = select(CotReportRow).where(CotReportRow.contract_code == contract_code)
        if as_of is not None:
            query = query.where(CotReportRow.release_date <= as_of)
        return [_report(r) for r in self.session.scalars(query.order_by(CotReportRow.report_date))]
