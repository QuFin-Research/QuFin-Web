"""The API must serve the same numbers as the web app's offline mock.

tests/fixtures/web_parity.json is produced from the TypeScript code by
scripts/web-parity-fixture.mts; regenerate it whenever mock-data.ts or engine.ts change.
Floats are compared to 1e-9 relative: Python and V8 can differ in the last bit of log/exp/cos.
"""

import json
from pathlib import Path

import pytest

from app.data.repository import SampleMarketRepository
from app.domain.backtest import backtest_decision_rule, run_backtest
from app.domain.market import hit_rate_for, regime_for
from app.schemas.backtest import DecisionRuleBacktestRequest, StrategyBacktestRequest

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "web_parity.json").read_text())
repo = SampleMarketRepository()


def assert_matches(actual, expected, path="$"):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), path
        for key in expected:
            assert_matches(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            assert_matches(a, e, f"{path}[{i}]")
    elif isinstance(expected, float) or isinstance(actual, float):
        assert actual == pytest.approx(expected, rel=1e-9, abs=1e-12), path
    else:
        assert actual == expected, path


def dump(model):
    return model.model_dump(by_alias=True)


# Fields only live (API-computed) scorecards fill; the offline mock has sample scores only.
LIVE_ONLY = {"data", "confidence", "overall_confidence", "as_of", "indicators", "pending"}


def test_country_scores_match_web():
    sample = [c.model_dump(by_alias=True, exclude=LIVE_ONLY) for c in repo.get_country_scores()]
    assert_matches(sample, FIXTURE["countries"])
    assert all(c.data == "sample" for c in repo.get_country_scores())


@pytest.mark.parametrize("symbol", sorted(FIXTURE["assets"]))
def test_series_and_backtests_match_web(symbol):
    expected = FIXTURE["assets"][symbol]
    candles, signals = repo.get_candles(symbol), repo.get_signals(symbol)
    asset = repo.get_asset(symbol)

    strategy = []
    for item in expected["strategy"]:
        params = StrategyBacktestRequest(
            kind="strategy",
            symbol=symbol,
            strategy=item["strategy"],
            min_edge=0.05,
            rebalance_days=5,
            cost_bps=3,
            lookback_days=504,
        )
        stats = run_backtest(candles, signals, params).stats
        strategy.append({"strategy": item["strategy"], "stats": dump(stats)})

    rule = []
    for item in expected["rule"]:
        params = DecisionRuleBacktestRequest(
            kind="decision-rule",
            symbol=symbol,
            direction=item["direction"],
            stop_pct=0.01,
            target_pct=0.02,
            max_hold_days=10,
            min_edge=0.05,
            cost_bps=2,
        )
        r = backtest_decision_rule(candles, signals, params)
        rule.append(
            {
                "direction": item["direction"],
                "trades": len(r.trades),
                "firstTrade": dump(r.trades[0]) if r.trades else None,
                "winRate": r.win_rate,
                "avgR": r.avg_r,
                "profitFactor": None if r.profit_factor == float("inf") else r.profit_factor,
                "finalCumR": r.curve[-1].cum_r if r.curve else 0,
            }
        )

    actual = {
        "candleCount": len(candles),
        "firstCandle": dump(candles[0]),
        "lastCandle": dump(candles[-1]),
        "lastSignal": dump(signals[-1]),
        "regime": regime_for(candles),
        "hitRate": hit_rate_for(candles, signals),
        "drivers": [dump(d) for d in repo.get_drivers(asset, signals[-1])],
        "strategy": strategy,
        "rule": rule,
    }
    assert_matches(actual, expected)
