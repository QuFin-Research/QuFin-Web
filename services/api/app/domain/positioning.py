"""Speculative positioning metrics from COT reports.

Non-commercial ("large speculator") net positioning is the classic sentiment gauge. The COT
index puts the latest net position within its range over the trailing window:
0 = the most bearish of the window, 100 = the most bullish. Readings near the extremes mark
crowded trades, which tend to be contrarian signals rather than trend confirmations.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.data.positioning_catalog import CotContract
from app.stores.positioning import CotReport

COT_INDEX_WEEKS = 156  # three years
MIN_INDEX_WEEKS = 26


@dataclass(frozen=True)
class PositioningPoint:
    report_date: date
    release_date: date
    open_interest: int
    net: int
    net_pct_oi: float
    cot_index: float | None


def _net(report: CotReport, contract: CotContract) -> int:
    return contract.sign * (report.noncomm_long - report.noncomm_short)


def series(contract: CotContract, reports: Sequence[CotReport]) -> list[PositioningPoint]:
    """Metrics for every report, each computed only from reports up to that week."""
    nets = [_net(r, contract) for r in reports]
    points = []
    for i, r in enumerate(reports):
        window = nets[max(0, i + 1 - COT_INDEX_WEEKS) : i + 1]
        lo, hi = min(window), max(window)
        index = None
        if len(window) >= MIN_INDEX_WEEKS:
            index = 50.0 if hi == lo else round(100 * (nets[i] - lo) / (hi - lo), 1)
        points.append(
            PositioningPoint(
                report_date=r.report_date,
                release_date=r.release_date,
                open_interest=r.open_interest,
                net=nets[i],
                net_pct_oi=round(100 * nets[i] / r.open_interest, 2) if r.open_interest else 0.0,
                cot_index=index,
            )
        )
    return points
