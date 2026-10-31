"""Mirrors the Decision type in apps/web/src/features/journal/utils/store.ts."""

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.backtest import SymbolStr
from app.schemas.base import ApiModel
from app.schemas.market import Direction

PositivePrice = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class DecisionBacktestSummary(ApiModel):
    """Rule-backtest summary captured when the decision was logged."""

    trades: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=1)
    avg_r: float = Field(allow_inf_nan=False)


class DecisionCreate(ApiModel):
    symbol: SymbolStr
    direction: Direction
    entry: PositivePrice
    stop: PositivePrice
    target: PositivePrice
    risk_pct: float = Field(gt=0, le=10, description="Risk per trade as a % of account")
    max_hold_days: int = Field(ge=1, le=250)
    signal_prob_up: float = Field(ge=0, le=1, description="QuFin signal when the decision was made")
    backtest: DecisionBacktestSummary | None
    note: str = Field(max_length=2000)

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def levels_match_direction(self) -> Self:
        sign = 1 if self.direction == "long" else -1
        if sign * (self.entry - self.stop) <= 0:
            raise ValueError(f"stop must be on the losing side of entry for a {self.direction}")
        if sign * (self.target - self.entry) <= 0:
            raise ValueError(f"target must be on the winning side of entry for a {self.direction}")
        return self


class Decision(DecisionCreate):
    id: str
    created_at: datetime
