import math
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app.data.repository import MarketRepository, get_market_repository
from app.domain.backtest import backtest_decision_rule, run_backtest
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResult,
    DecisionRuleBacktestResult,
    StrategyBacktestRequest,
    StrategyBacktestResult,
)

router = APIRouter(prefix="/v1", tags=["backtests"])


@router.post("/backtests", response_model=BacktestResult)
def create_backtest(
    request: Annotated[BacktestRequest, Body()],
    repo: Annotated[MarketRepository, Depends(get_market_repository)],
) -> StrategyBacktestResult | DecisionRuleBacktestResult:
    """Run a strategy backtest (`kind: "strategy"`) or replay a trade plan on past signals
    (`kind: "decision-rule"`). Results are hypothetical and exclude financing costs."""
    candles = repo.get_candles(request.symbol)
    signals = repo.get_signals(request.symbol)
    if len(candles) < 2:
        raise HTTPException(status_code=422, detail="Unknown symbol")

    if isinstance(request, StrategyBacktestRequest):
        run = run_backtest(candles, signals, request)
        return StrategyBacktestResult(
            symbol=request.symbol, as_of=repo.as_of, equity=run.equity, stats=run.stats
        )

    rule = backtest_decision_rule(candles, signals, request)
    return DecisionRuleBacktestResult(
        symbol=request.symbol,
        as_of=repo.as_of,
        trades=rule.trades,
        win_rate=rule.win_rate,
        avg_r=rule.avg_r,
        expectancy_pct=rule.expectancy_pct,
        profit_factor=None if math.isinf(rule.profit_factor) else rule.profit_factor,
        curve=rule.curve,
    )
