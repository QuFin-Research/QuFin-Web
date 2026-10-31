"""Mirrors apps/web/src/features/market/api/types.ts."""

from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel

AssetClass = Literal["FX", "Metals", "Energy", "Crypto"]
Direction = Literal["long", "short"]
Conviction = Literal["low", "medium", "high"]
Regime = Literal["Uptrend", "Downtrend", "Range", "High volatility"]
DriverCategory = Literal["Fundamental", "Technical", "Positioning", "Sentiment", "Macro"]
ScoreDimension = Literal["growth", "inflation", "labour", "policy", "sentiment"]


class Asset(ApiModel):
    symbol: str
    name: str
    asset_class: AssetClass
    precision: int = Field(description="Decimal places used when displaying prices")


class Candle(ApiModel):
    time: str = Field(description="Trading day, ISO date (YYYY-MM-DD)")
    open: float
    high: float
    low: float
    close: float


class Signal(ApiModel):
    """Model output for one asset on one day, made at that day's close and
    forecasting the direction of the next `horizonDays` trading days."""

    time: str
    prob_up: float = Field(description="Probability that price is higher after the horizon (0-1)")
    direction: Direction
    conviction: Conviction
    horizon_days: int


class SignalDriver(ApiModel):
    name: str
    category: DriverCategory
    contribution: float = Field(
        description="Signed contribution to the score; positive supports a long"
    )


class AssetSnapshot(ApiModel):
    asset: Asset
    last_price: float
    change_pct: float
    regime: Regime
    signal: Signal
    hit_rate: float = Field(description="Directional hit rate of past signals (walk-forward)")


class AssetDetail(AssetSnapshot):
    candles: list[Candle]
    signals: list[Signal]
    drivers: list[SignalDriver]


class CountryScores(ApiModel):
    growth: int = Field(ge=-3, le=3)
    inflation: int = Field(ge=-3, le=3)
    labour: int = Field(ge=-3, le=3)
    policy: int = Field(ge=-3, le=3)
    sentiment: int = Field(ge=-3, le=3)


class CountryScore(ApiModel):
    code: str
    country: str
    currency: str
    scores: CountryScores = Field(
        description="Each dimension scored -3 (very weak) to +3 (very strong)"
    )
    overall: float
