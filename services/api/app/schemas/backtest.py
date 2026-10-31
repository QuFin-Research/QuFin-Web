"""Mirrors apps/web/src/features/backtest/lib/engine.ts, with the series looked up by symbol
on the server instead of being sent by the client."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.data.sample import HISTORY_DAYS
from app.schemas.base import ApiModel
from app.schemas.market import Direction

StrategyKind = Literal["all-signals", "high-conviction", "buy-hold"]
SymbolStr = Annotated[str, Field(min_length=2, max_length=12, pattern=r"^[A-Za-z0-9]+$")]


class _BacktestRequestBase(ApiModel):
    symbol: SymbolStr
    min_edge: float = Field(ge=0, le=0.5, description="Minimum |probUp - 0.5| to take a position")
    cost_bps: float = Field(
        ge=0,
        le=500,
        description="One-way cost in basis points (spread + commission + slippage)",
    )

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, value: str) -> str:
        return value.upper()


class StrategyBacktestRequest(_BacktestRequestBase):
    kind: Literal["strategy"]
    strategy: StrategyKind
    rebalance_days: int = Field(ge=1, le=60, description="Re-evaluate the position every N days")
    lookback_days: int = Field(
        ge=20,
        le=HISTORY_DAYS - 1,
        description="Number of most recent trading days to test",
    )


class DecisionRuleBacktestRequest(_BacktestRequestBase):
    kind: Literal["decision-rule"]
    direction: Direction
    stop_pct: float = Field(gt=0, le=0.5, description="Stop distance as a fraction of entry")
    target_pct: float = Field(gt=0, le=2, description="Target distance as a fraction of entry")
    max_hold_days: int = Field(ge=1, le=250)


BacktestRequest = Annotated[
    StrategyBacktestRequest | DecisionRuleBacktestRequest, Field(discriminator="kind")
]


class EquityPoint(ApiModel):
    time: str
    strategy: float
    benchmark: float
    drawdown: float


class BacktestStats(ApiModel):
    total_return: float
    benchmark_return: float
    cagr: float
    annual_vol: float
    sharpe: float
    max_drawdown: float
    hit_rate: float
    trades: int
    exposure: float


class StrategyBacktestResult(ApiModel):
    kind: Literal["strategy"] = "strategy"
    symbol: str
    as_of: str
    equity: list[EquityPoint]
    stats: BacktestStats


class RuleTrade(ApiModel):
    entry_time: str
    exit_time: str
    outcome: Literal["target", "stop", "time"]
    r: float = Field(description="Return in R multiples (1R = stop distance), after costs")


class CurvePoint(ApiModel):
    time: str
    cum_r: float


class DecisionRuleBacktestResult(ApiModel):
    kind: Literal["decision-rule"] = "decision-rule"
    symbol: str
    as_of: str
    trades: list[RuleTrade]
    win_rate: float
    avg_r: float
    expectancy_pct: float
    profit_factor: float | None = Field(
        description="Gross win / gross loss; null when there are wins but no losses (infinite)"
    )
    curve: list[CurvePoint]


BacktestResult = Annotated[
    StrategyBacktestResult | DecisionRuleBacktestResult, Field(discriminator="kind")
]
