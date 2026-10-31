"""Backtest engine — a port of apps/web/src/features/backtest/lib/engine.ts.

Conventions: a signal is formed at day t's close and acts on day t+1's return (no look-ahead).
Costs are charged on every change in position. Production runs will use point-in-time data
with purged walk-forward validation; the maths here stays the same.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.data.sample import js_sum, js_to_fixed
from app.schemas.backtest import (
    BacktestStats,
    CurvePoint,
    DecisionRuleBacktestRequest,
    EquityPoint,
    RuleTrade,
    StrategyBacktestRequest,
)
from app.schemas.market import Candle, Signal

TRADING_DAYS = 252


def _target_position(signal: Signal, params: StrategyBacktestRequest) -> int:
    if params.strategy == "buy-hold":
        return 1
    edge = signal.prob_up - 0.5
    threshold = (
        max(params.min_edge, 0.1) if params.strategy == "high-conviction" else params.min_edge
    )
    if abs(edge) < threshold:
        return 0
    return 1 if edge > 0 else -1


@dataclass(frozen=True)
class StrategyRun:
    equity: list[EquityPoint]
    stats: BacktestStats


def run_backtest(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    params: StrategyBacktestRequest,
) -> StrategyRun:
    start = max(1, len(candles) - params.lookback_days)
    cost = params.cost_bps / 10000

    equity = benchmark = peak = 1.0
    position = 0
    period_pnl = 0.0
    wins = periods = trades = days_in_market = 0
    max_drawdown = 0.0
    daily: list[float] = []
    points: list[EquityPoint] = []

    for i in range(start, len(candles)):
        if (i - start) % params.rebalance_days == 0:
            if position != 0:
                periods += 1
                if period_pnl > 0:
                    wins += 1
            period_pnl = 0.0
            nxt = _target_position(signals[i - 1], params)
            if nxt != position:
                equity *= 1 - cost * abs(nxt - position)
                if nxt != 0:
                    trades += 1
                position = nxt

        ret = candles[i].close / candles[i - 1].close - 1
        pnl = position * ret
        equity *= 1 + pnl
        benchmark *= 1 + ret
        period_pnl += pnl
        daily.append(pnl)
        if position != 0:
            days_in_market += 1

        peak = max(peak, equity)
        dd = equity / peak - 1
        max_drawdown = min(max_drawdown, dd)
        points.append(
            EquityPoint(time=candles[i].time, strategy=equity, benchmark=benchmark, drawdown=dd)
        )
    if position != 0:
        periods += 1
        if period_pnl > 0:
            wins += 1

    n = len(daily) or 1
    mean = js_sum(daily) / n
    sd = math.sqrt(js_sum((r - mean) ** 2 for r in daily) / n)
    years = n / TRADING_DAYS

    return StrategyRun(
        equity=points,
        stats=BacktestStats(
            total_return=equity - 1,
            benchmark_return=benchmark - 1,
            cagr=equity ** (1 / years) - 1 if equity > 0 else -1,
            annual_vol=sd * math.sqrt(TRADING_DAYS),
            sharpe=(mean / sd) * math.sqrt(TRADING_DAYS) if sd > 0 else 0,
            max_drawdown=max_drawdown,
            hit_rate=wins / periods if periods else 0,
            trades=trades,
            exposure=days_in_market / n,
        ),
    )


# --- Decision-rule backtest ----------------------------------------------------------------
# "Backtest this decision": replays the user's trade plan (direction, stop and target
# distances, max holding days) on every past day where the QuFin signal agreed with that
# direction at the required conviction, and reports how that plan would have performed.


@dataclass(frozen=True)
class RuleRun:
    trades: list[RuleTrade]
    win_rate: float
    avg_r: float
    expectancy_pct: float
    profit_factor: float
    curve: list[CurvePoint]


def backtest_decision_rule(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    rule: DecisionRuleBacktestRequest,
) -> RuleRun:
    trades: list[RuleTrade] = []
    sign = 1 if rule.direction == "long" else -1
    cost_r = (2 * rule.cost_bps) / 10000 / rule.stop_pct
    last = len(candles) - 1

    i = 0
    while i < last:
        s = signals[i]
        agrees = (1 if s.prob_up >= 0.5 else -1) == sign
        if not agrees or abs(s.prob_up - 0.5) < rule.min_edge:
            i += 1
            continue

        # Enter at the next day's open; exit on stop, target or time.
        entry = candles[i + 1].open
        stop = entry * (1 - sign * rule.stop_pct)
        target = entry * (1 + sign * rule.target_pct)
        exit_idx = min(i + rule.max_hold_days, last)
        outcome = "time"
        exit_price = candles[exit_idx].close

        for j in range(i + 1, min(i + rule.max_hold_days, last) + 1):
            c = candles[j]
            hit_stop = c.low <= stop if sign > 0 else c.high >= stop
            hit_target = c.high >= target if sign > 0 else c.low <= target
            # If both are touched on the same bar, assume the stop came first (conservative).
            if hit_stop:
                outcome, exit_price, exit_idx = "stop", stop, j
                break
            if hit_target:
                outcome, exit_price, exit_idx = "target", target, j
                break

        move_pct = (sign * (exit_price - entry)) / entry
        trades.append(
            RuleTrade(
                entry_time=candles[i + 1].time,
                exit_time=candles[exit_idx].time,
                outcome=outcome,
                r=move_pct / rule.stop_pct - cost_r,
            )
        )
        i = exit_idx + 1

    cum_r = 0.0
    curve: list[CurvePoint] = []
    for t in trades:
        cum_r += t.r
        curve.append(CurvePoint(time=t.exit_time, cum_r=js_to_fixed(cum_r, 2)))
    wins = [t for t in trades if t.r > 0]
    gross_win = js_sum(t.r for t in wins)
    gross_loss = abs(js_sum(t.r for t in trades if t.r <= 0))
    avg_r = cum_r / len(trades) if trades else 0.0

    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:  # no losing trades: infinite if anything was won
        profit_factor = math.inf if gross_win > 0 else 0.0

    return RuleRun(
        trades=trades,
        win_rate=len(wins) / len(trades) if trades else 0.0,
        avg_r=avg_r,
        expectancy_pct=avg_r * rule.stop_pct,
        profit_factor=profit_factor,
        curve=curve,
    )
