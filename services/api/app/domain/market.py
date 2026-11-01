"""Snapshot, regime and hit-rate analytics over any MarketRepository."""

import math
from collections.abc import Sequence

from app.data.repository import MarketRepository
from app.data.sample import js_sum
from app.schemas.market import AssetDetail, AssetSnapshot, Candle, Regime, Signal


def regime_for(candles: Sequence[Candle]) -> Regime:
    recent = candles[-40:]
    rets = [math.log(c.close / recent[i].close) for i, c in enumerate(recent[1:])]
    mean = js_sum(rets) / len(rets)
    vol = math.sqrt(js_sum((r - mean) ** 2 for r in rets) / len(rets))
    long_rets = candles[-260:]
    long_vol = math.sqrt(
        js_sum(math.log(c.close / long_rets[i].close) ** 2 for i, c in enumerate(long_rets[1:]))
        / (len(long_rets) - 1)
    )
    if vol > long_vol * 1.35:
        return "High volatility"
    trend_t = (mean / (vol or 1)) * math.sqrt(len(rets))
    if trend_t > 1:
        return "Uptrend"
    if trend_t < -1:
        return "Downtrend"
    return "Range"


def hit_rate_for(candles: Sequence[Candle], signals: Sequence[Signal]) -> float:
    """Share of past signals whose direction matched the forward return over the horizon."""
    if not signals:
        return 0.0
    horizon = signals[0].horizon_days
    hits = total = 0
    for i in range(len(candles) - horizon):
        fwd = candles[i + horizon].close - candles[i].close
        if (fwd > 0) == (signals[i].prob_up >= 0.5):
            hits += 1
        total += 1
    return hits / total if total else 0.0


def snapshot_for(repo: MarketRepository, symbol: str) -> AssetSnapshot | None:
    asset = repo.get_asset(symbol)
    candles = repo.get_candles(symbol)
    signals = repo.get_signals(symbol)
    if asset is None or len(candles) < 2 or not signals:
        return None
    last, prev = candles[-1], candles[-2]
    return AssetSnapshot(
        data=repo.origin,
        asset=asset,
        last_price=last.close,
        change_pct=(last.close / prev.close - 1) * 100,
        regime=regime_for(candles),
        signal=signals[-1],
        hit_rate=hit_rate_for(candles, signals),
    )


def list_snapshots(repo: MarketRepository) -> list[AssetSnapshot]:
    snapshots = (snapshot_for(repo, a.symbol) for a in repo.list_assets())
    return [s for s in snapshots if s is not None]


def asset_detail(repo: MarketRepository, symbol: str) -> AssetDetail | None:
    snapshot = snapshot_for(repo, symbol)
    if snapshot is None:
        return None
    return AssetDetail(
        **dict(snapshot),
        candles=list(repo.get_candles(symbol)),
        signals=list(repo.get_signals(symbol)),
        drivers=repo.get_drivers(snapshot.asset, snapshot.signal),
    )
