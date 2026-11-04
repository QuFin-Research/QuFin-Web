"""Speculative positioning metrics from COT reports.

The net position of the contract's speculative group (app/data/positioning_catalog.py: leveraged
funds for financial futures, non-commercial traders for commodities) is the classic sentiment
gauge. The COT index puts the latest net position within its range over the trailing window:
0 = the most bearish of the window, 100 = the most bullish. Readings near the extremes mark
crowded trades, which tend to be contrarian signals rather than trend confirmations.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.data.positioning_catalog import CotContract
from app.stores.positioning import Positions

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
    # Asset managers' net, in the asset's direction: financial futures only.
    asset_manager_net: int | None


def _net(p: Positions, contract: CotContract) -> int:
    return contract.sign * (p.long - p.short)


def _asset_manager_net(p: Positions, contract: CotContract) -> int | None:
    if p.asset_mgr_long is None or p.asset_mgr_short is None:
        return None
    return contract.sign * (p.asset_mgr_long - p.asset_mgr_short)


def series(contract: CotContract, weeks: Sequence[Positions]) -> list[PositioningPoint]:
    """Metrics for every week, each computed only from weeks up to it."""
    nets = [_net(p, contract) for p in weeks]
    points = []
    for i, p in enumerate(weeks):
        window = nets[max(0, i + 1 - COT_INDEX_WEEKS) : i + 1]
        lo, hi = min(window), max(window)
        index = None
        if len(window) >= MIN_INDEX_WEEKS:
            index = 50.0 if hi == lo else round(100 * (nets[i] - lo) / (hi - lo), 1)
        points.append(
            PositioningPoint(
                report_date=p.report_date,
                release_date=p.release_date,
                open_interest=p.open_interest,
                net=nets[i],
                net_pct_oi=round(100 * nets[i] / p.open_interest, 2) if p.open_interest else 0.0,
                cot_index=index,
                asset_manager_net=_asset_manager_net(p, contract),
            )
        )
    return points
