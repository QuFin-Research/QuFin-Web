"""Backtest maths on small hand-built series where the right answer is known."""

import math

import pytest

from app.domain.backtest import backtest_decision_rule, run_backtest
from app.schemas.backtest import DecisionRuleBacktestRequest, StrategyBacktestRequest
from app.schemas.market import Candle, Signal


def make_candles(closes, *, opens=None, highs=None, lows=None):
    candles = []
    for i, close in enumerate(closes):
        open_ = opens[i] if opens else (closes[i - 1] if i else close)
        high = highs[i] if highs else max(open_, close)
        low = lows[i] if lows else min(open_, close)
        candles.append(
            Candle(time=f"2026-01-{i + 1:02d}", open=open_, high=high, low=low, close=close)
        )
    return candles


def make_signals(probs):
    return [
        Signal(
            time=f"2026-01-{i + 1:02d}",
            prob_up=p,
            direction="long" if p >= 0.5 else "short",
            conviction="high" if abs(p - 0.5) >= 0.1 else "low",
            horizon_days=1,
        )
        for i, p in enumerate(probs)
    ]


def strategy(**overrides):
    params = {
        "kind": "strategy",
        "symbol": "TEST",
        "strategy": "all-signals",
        "min_edge": 0.05,
        "rebalance_days": 1,
        "cost_bps": 0,
        "lookback_days": 20,
    }
    return StrategyBacktestRequest(**(params | overrides))


def rule(**overrides):
    params = {
        "kind": "decision-rule",
        "symbol": "TEST",
        "direction": "long",
        "stop_pct": 0.01,
        "target_pct": 0.02,
        "max_hold_days": 3,
        "min_edge": 0.05,
        "cost_bps": 0,
    }
    return DecisionRuleBacktestRequest(**(params | overrides))


CLOSES = [100, 102, 101, 104, 103, 106, 105, 108]


def test_buy_and_hold_tracks_the_benchmark():
    candles = make_candles(CLOSES)
    run = run_backtest(candles, make_signals([0.5] * len(CLOSES)), strategy(strategy="buy-hold"))
    assert run.stats.total_return == pytest.approx(108 / 100 - 1)
    assert run.stats.benchmark_return == pytest.approx(108 / 100 - 1)
    assert run.stats.exposure == 1
    assert run.stats.trades == 1
    assert len(run.equity) == len(CLOSES) - 1


def test_costs_are_charged_on_position_changes():
    candles = make_candles(CLOSES)
    signals = make_signals([0.5] * len(CLOSES))
    run = run_backtest(candles, signals, strategy(strategy="buy-hold", cost_bps=10))
    assert run.stats.total_return == pytest.approx((1 - 0.001) * 1.08 - 1)


def test_signals_act_on_the_next_day_only():
    # Zig-zag prices. A signal that already knows today's move must not profit:
    # it is only applied to the following day, which reverses.
    closes = [100, 101, 100, 101, 100, 101, 100, 101, 100]
    same_day = [0.5] + [0.7 if closes[i] > closes[i - 1] else 0.3 for i in range(1, len(closes))]
    run = run_backtest(make_candles(closes), make_signals(same_day), strategy())
    assert run.stats.total_return < 0

    # A genuine one-day-ahead forecast is right every time.
    ahead = [0.7 if closes[i + 1] > closes[i] else 0.3 for i in range(len(closes) - 1)] + [0.5]
    run = run_backtest(make_candles(closes), make_signals(ahead), strategy())
    assert run.stats.total_return > 0
    assert run.stats.hit_rate == 1


def test_min_edge_filters_weak_signals():
    candles = make_candles(CLOSES)
    run = run_backtest(candles, make_signals([0.52] * len(CLOSES)), strategy(min_edge=0.05))
    assert run.stats.trades == 0
    assert run.stats.exposure == 0
    assert run.stats.total_return == 0


def test_high_conviction_needs_at_least_ten_points_of_edge():
    candles = make_candles(CLOSES)
    signals = make_signals([0.57] * len(CLOSES))
    assert run_backtest(candles, signals, strategy()).stats.trades == 1
    assert run_backtest(candles, signals, strategy(strategy="high-conviction")).stats.trades == 0


def test_max_drawdown_and_rebalance_period():
    candles = make_candles([100, 110, 99, 99])
    run = run_backtest(candles, make_signals([0.5] * 4), strategy(strategy="buy-hold"))
    assert run.stats.max_drawdown == pytest.approx(99 / 110 - 1)

    # With a 2-day rebalance the short signal on day 1 is not acted on until day 3.
    signals = make_signals([0.7, 0.3, 0.7, 0.7])
    run = run_backtest(candles, signals, strategy(rebalance_days=2))
    assert [p.strategy for p in run.equity][:2] == pytest.approx([1.1, 0.99])


def test_rule_target_hit():
    candles = make_candles(
        [100, 100, 101, 101], opens=[100, 100, 100, 101], highs=[100, 100.5, 102.5, 101]
    )
    result = backtest_decision_rule(candles, make_signals([0.7, 0.5, 0.5, 0.5]), rule())
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert (trade.entry_time, trade.exit_time, trade.outcome) == (
        "2026-01-02",
        "2026-01-03",
        "target",
    )
    assert trade.r == pytest.approx(2)
    assert result.profit_factor == math.inf


def test_rule_assumes_stop_first_when_both_levels_touched():
    candles = make_candles(
        [100, 100, 100], opens=[100, 100, 100], highs=[100, 103, 100], lows=[100, 98, 100]
    )
    result = backtest_decision_rule(candles, make_signals([0.7, 0.5, 0.5]), rule(cost_bps=5))
    trade = result.trades[0]
    assert trade.outcome == "stop"
    # -1R, plus a round trip of 2 x 5 bps on a 1% stop = 0.1R
    assert trade.r == pytest.approx(-1 - 0.1)
    assert result.win_rate == 0
    assert result.profit_factor == 0


def test_rule_time_exit_and_short_direction():
    closes = [100, 100, 99.5, 99.6, 99.4, 99]
    candles = make_candles(closes, opens=[100, 100, *closes[1:-1]])
    result = backtest_decision_rule(
        candles, make_signals([0.3] + [0.5] * 5), rule(direction="short", max_hold_days=3)
    )
    trade = result.trades[0]
    assert (trade.outcome, trade.exit_time) == ("time", "2026-01-04")
    assert trade.r == pytest.approx((100 - 99.6) / 100 / 0.01)


def test_rule_ignores_signals_against_the_plan():
    candles = make_candles(CLOSES)
    result = backtest_decision_rule(candles, make_signals([0.3] * len(CLOSES)), rule())
    assert result.trades == []
    assert result.avg_r == 0
    assert result.win_rate == 0
