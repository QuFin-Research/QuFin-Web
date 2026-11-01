"""Mirrors apps/web/src/features/market/api/types.ts."""

from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin

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
    data: DataOrigin = Field(description=ORIGIN_DESCRIPTION)
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
    growth: float = Field(ge=-3, le=3)
    inflation: float = Field(ge=-3, le=3)
    labour: float = Field(ge=-3, le=3)
    policy: float = Field(ge=-3, le=3)
    sentiment: float = Field(ge=-3, le=3)


class PillarConfidence(ApiModel):
    growth: float = Field(ge=0, le=1)
    inflation: float = Field(ge=0, le=1)
    labour: float = Field(ge=0, le=1)
    policy: float = Field(ge=0, le=1)
    sentiment: float = Field(ge=0, le=1)


class ScorecardIndicator(ApiModel):
    id: str
    title: str
    pillar: ScoreDimension
    source_name: str | None
    period: date | None = Field(description="Latest period used")
    value: float | None = Field(description="Reading after the transform (level or % y/y)")
    score: float | None = Field(description="-3..+3 against its own 10-year history")
    level_score: float | None = Field(description="Where it stands (level or change over a year)")
    momentum_score: float | None = Field(description="How fast it is moving (3-month change)")
    weight: float = Field(description="Importance x timeliness; 0 when not usable")
    usable: bool
    status: str


class PendingRelease(ApiModel):
    series_id: str
    title: str
    source_name: str | None
    period: date | None = Field(description="The period expected next")
    source_release: date | None = Field(description="When the source publishes (or did)")
    fred_release: date | None = Field(description="When FRED shows it")
    reason: str


class CountryScore(ApiModel):
    code: str
    country: str
    currency: str
    scores: CountryScores = Field(
        description="Each pillar -3 (very weak) to +3 (very strong): growth strong, inflation "
        "hot, labour tight, policy tight, sentiment upbeat"
    )
    overall: float
    data: Literal["live", "sample"] = Field(
        default="sample", description="live: computed from the point-in-time macro store"
    )
    confidence: PillarConfidence | None = Field(
        default=None,
        description="Share of each pillar's full evidence that is fresh and usable. Lower "
        "confidence means size positions smaller; it never changes the score itself",
    )
    overall_confidence: float | None = None
    as_of: date | None = None
    indicators: list[ScorecardIndicator] = Field(default_factory=list)
    pending: list[PendingRelease] = Field(
        default_factory=list, description="Releases still to come that may move the scores"
    )
