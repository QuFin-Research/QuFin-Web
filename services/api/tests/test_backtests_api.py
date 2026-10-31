import math

from app.domain import backtest
from app.routes import backtests


def strategy_body(**overrides):
    body = {
        "kind": "strategy",
        "symbol": "EURUSD",
        "strategy": "all-signals",
        "minEdge": 0.05,
        "rebalanceDays": 5,
        "costBps": 3,
        "lookbackDays": 504,
    }
    return body | overrides


def rule_body(**overrides):
    body = {
        "kind": "decision-rule",
        "symbol": "XAUUSD",
        "direction": "long",
        "stopPct": 0.01,
        "targetPct": 0.02,
        "maxHoldDays": 10,
        "minEdge": 0.05,
        "costBps": 2,
    }
    return body | overrides


def test_strategy_backtest(client):
    res = client.post("/v1/backtests", json=strategy_body())
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "strategy"
    assert body["asOf"] == "2026-10-30"
    assert len(body["equity"]) == 504
    assert set(body["stats"]) == {
        "totalReturn",
        "benchmarkReturn",
        "cagr",
        "annualVol",
        "sharpe",
        "maxDrawdown",
        "hitRate",
        "trades",
        "exposure",
    }
    assert body["stats"]["maxDrawdown"] <= 0


def test_decision_rule_backtest(client):
    res = client.post("/v1/backtests", json=rule_body(symbol="xauusd"))
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "decision-rule"
    assert body["symbol"] == "XAUUSD"
    assert len(body["trades"]) == len(body["curve"]) > 0
    assert body["curve"][-1]["cumR"] == round(sum(t["r"] for t in body["trades"]), 2)
    assert {t["outcome"] for t in body["trades"]} <= {"target", "stop", "time"}


def test_profit_factor_is_null_when_there_are_no_losses(client, monkeypatch):
    real = backtest.backtest_decision_rule

    def no_losses(*args):
        result = real(*args)
        return backtest.RuleRun(**{**result.__dict__, "profit_factor": math.inf})

    monkeypatch.setattr(backtests, "backtest_decision_rule", no_losses)
    assert client.post("/v1/backtests", json=rule_body()).json()["profitFactor"] is None


def test_backtest_validation(client):
    cases = [
        strategy_body(kind="monte-carlo"),
        strategy_body(strategy="martingale"),
        strategy_body(minEdge=0.6),
        strategy_body(rebalanceDays=0),
        strategy_body(lookbackDays=5000),
        strategy_body(costBps=-1),
        strategy_body(symbol="EUR/USD"),
        strategy_body(unexpected=True),
        rule_body(stopPct=0),
        rule_body(direction="sideways"),
        rule_body(maxHoldDays=0),
        {"symbol": "EURUSD"},
    ]
    for body in cases:
        assert client.post("/v1/backtests", json=body).status_code == 422, body


def test_backtest_unknown_symbol(client):
    res = client.post("/v1/backtests", json=strategy_body(symbol="DOGEUSD"))
    assert res.status_code == 422
    assert res.json() == {"detail": "Unknown symbol"}
