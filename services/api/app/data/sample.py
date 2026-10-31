"""Deterministic sample market data — a port of apps/web/src/features/market/lib/mock-data.ts.

Prices follow a random walk with a slowly-changing hidden drift. The sample "model" sees a
noisy reading of that drift, which gives signals a realistic edge (roughly 55-60% directional
hit rate, higher on high conviction) rather than the inflated numbers a demo usually shows.

Everything is seeded by symbol and anchored to AS_OF, and the arithmetic follows the
TypeScript generator step by step (32-bit integer maths, left-to-right sums, JS rounding),
so the API and the web app's offline mock serve the same numbers.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from app.schemas.market import (
    Asset,
    AssetClass,
    Candle,
    Conviction,
    CountryScore,
    CountryScores,
    DriverCategory,
    Signal,
    SignalDriver,
)

AS_OF = "2026-10-30"
HISTORY_DAYS = 780
SIGNAL_HORIZON_DAYS = 5

_U32 = 0xFFFFFFFF


@dataclass(frozen=True)
class AssetSpec:
    symbol: str
    name: str
    asset_class: AssetClass
    precision: int
    base_price: float
    daily_vol: float

    def to_asset(self) -> Asset:
        return Asset(
            symbol=self.symbol,
            name=self.name,
            asset_class=self.asset_class,
            precision=self.precision,
        )


ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec("EURUSD", "Euro / US Dollar", "FX", 5, 1.08, 0.0045),
    AssetSpec("GBPUSD", "British Pound / US Dollar", "FX", 5, 1.27, 0.005),
    AssetSpec("USDJPY", "US Dollar / Japanese Yen", "FX", 3, 148, 0.0055),
    AssetSpec("AUDUSD", "Australian Dollar / US Dollar", "FX", 5, 0.66, 0.006),
    AssetSpec("XAUUSD", "Gold", "Metals", 2, 2350, 0.009),
    AssetSpec("XAGUSD", "Silver", "Metals", 3, 28, 0.016),
    AssetSpec("WTI", "WTI Crude Oil", "Energy", 2, 78, 0.019),
    AssetSpec("BRENT", "Brent Crude Oil", "Energy", 2, 82, 0.018),
    AssetSpec("NATGAS", "Natural Gas (Henry Hub)", "Energy", 3, 2.6, 0.032),
    AssetSpec("BTCUSD", "Bitcoin", "Crypto", 0, 64000, 0.028),
    AssetSpec("ETHUSD", "Ether", "Crypto", 1, 3100, 0.034),
)
_SPECS = {spec.symbol: spec for spec in ASSETS}


# --- JavaScript-compatible primitives ------------------------------------------------------


def _imul(a: int, b: int) -> int:
    """Math.imul, on unsigned 32-bit representations."""
    return (a * b) & _U32


def hash_string(value: str) -> int:
    """FNV-1a over UTF-16 code units, as hashString() in the web app."""
    data = value.encode("utf-16-le")
    h = 2166136261
    for i in range(0, len(data), 2):
        h = _imul(h ^ (data[i] | data[i + 1] << 8), 16777619)
    return h


def create_rng(seed: int):
    """mulberry32 — small, fast, seedable PRNG returning floats in [0, 1)."""
    a = seed & _U32

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & _U32
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & _U32) ^ t
        return ((t ^ (t >> 14)) & _U32) / 4294967296

    return rng


def gaussian(rng) -> float:
    u = max(rng(), 1e-12)
    v = rng()
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def js_sum(values) -> float:
    """Left-to-right float sum, as Array.reduce. (Python's sum() compensates since 3.12.)"""
    total = 0.0
    for v in values:
        total += v
    return total


def js_round(x: float) -> int:
    """Math.round: halves round towards +infinity."""
    return math.floor(x + 0.5)


def js_to_fixed(x: float, digits: int) -> float:
    """Number(x.toFixed(digits)): exact decimal value, halves rounded away from zero."""
    return float(Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


# --- Series generator ----------------------------------------------------------------------


def _trading_days(count: int) -> list[str]:
    """Weekday dates ending at AS_OF, oldest first."""
    days: list[str] = []
    d = date.fromisoformat(AS_OF)
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d -= timedelta(days=1)
    return days[::-1]


def conviction_for(prob_up: float) -> Conviction:
    edge = abs(prob_up - 0.5)
    if edge >= 0.1:
        return "high"
    if edge >= 0.05:
        return "medium"
    return "low"


@dataclass(frozen=True)
class Series:
    candles: tuple[Candle, ...]
    signals: tuple[Signal, ...]


def get_spec(symbol: str) -> AssetSpec | None:
    return _SPECS.get(symbol)


@lru_cache(maxsize=len(ASSETS))
def get_series(symbol: str) -> Series | None:
    spec = _SPECS.get(symbol)
    if spec is None:
        return None

    rng = create_rng(hash_string(symbol))
    sigma = spec.daily_vol
    # Hidden drift: AR(1) with stationary s.d. of 0.15σ, persistent over a few weeks.
    phi = 0.9
    drift_sd = 0.15 * sigma
    drift_shock = drift_sd * math.sqrt(1 - phi * phi)

    raw: list[tuple[str, float, float, float, float]] = []
    signals: list[Signal] = []
    drift = 0.0
    price = float(spec.base_price)

    for time in _trading_days(HISTORY_DAYS):
        drift = phi * drift + drift_shock * gaussian(rng)
        # Weak pull back towards the starting level keeps multi-year ranges realistic.
        ret = drift - 0.01 * math.log(price / spec.base_price) + sigma * gaussian(rng)
        open_ = price
        close = open_ * math.exp(ret)
        # Draw order matches the TS: the high's wick first, then the low's.
        high = max(open_, close) * (1 + abs(gaussian(rng)) * sigma * 0.45)
        low = min(open_, close) * (1 - abs(gaussian(rng)) * sigma * 0.45)
        raw.append((time, open_, high, low, close))
        price = close

        # The model observes the hidden drift with noise.
        score = drift / drift_sd + gaussian(rng)
        prob_up = sigmoid(0.35 * score)
        signals.append(
            Signal(
                time=time,
                prob_up=prob_up,
                direction="long" if prob_up >= 0.5 else "short",
                conviction=conviction_for(prob_up),
                horizon_days=SIGNAL_HORIZON_DAYS,
            )
        )

    # Centre the path on the asset's reference level (geometric mean of closes).
    mean_log = js_sum(math.log(c[4]) for c in raw) / len(raw)
    scale = spec.base_price / math.exp(mean_log)
    candles = tuple(
        Candle(time=t, open=o * scale, high=h * scale, low=lo * scale, close=c * scale)
        for t, o, h, lo, c in raw
    )
    return Series(candles=candles, signals=tuple(signals))


# --- Driver explainer ----------------------------------------------------------------------

_DRIVERS: dict[AssetClass, tuple[tuple[str, DriverCategory], ...]] = {
    "FX": (
        ("2Y rate differential", "Fundamental"),
        ("CFTC net positioning", "Positioning"),
        ("PMI surprise index", "Macro"),
        ("20-day momentum", "Technical"),
        ("News sentiment", "Sentiment"),
    ),
    "Metals": (
        ("US real yields", "Fundamental"),
        ("US Dollar index trend", "Macro"),
        ("CFTC managed-money positioning", "Positioning"),
        ("50-day trend", "Technical"),
        ("Geopolitical risk index", "Sentiment"),
    ),
    "Energy": (
        ("EIA inventory surprise", "Fundamental"),
        ("OPEC+ supply outlook", "Macro"),
        ("CFTC net positioning", "Positioning"),
        ("Term-structure carry", "Technical"),
        ("Geopolitical risk index", "Sentiment"),
    ),
    "Crypto": (
        ("ETF net flows", "Positioning"),
        ("Global liquidity (M2)", "Macro"),
        ("Funding rates", "Positioning"),
        ("20-day momentum", "Technical"),
        ("Social sentiment", "Sentiment"),
    ),
}


def drivers_for(asset: Asset, signal: Signal) -> list[SignalDriver]:
    """Splits the latest score into signed driver contributions for the explainer."""
    rng = create_rng(hash_string(f"{asset.symbol}:{signal.time}"))
    defs = _DRIVERS[asset.asset_class]
    total = (signal.prob_up - 0.5) * 10
    raw = [gaussian(rng) * 0.8 + total / 5 for _ in defs]
    shift = (total - js_sum(raw)) / len(raw)
    drivers = [
        SignalDriver(name=name, category=category, contribution=js_to_fixed(raw[i] + shift, 2))
        for i, (name, category) in enumerate(defs)
    ]
    return sorted(drivers, key=lambda d: -abs(d.contribution))


# --- Country scorecards --------------------------------------------------------------------

_COUNTRIES = (
    ("US", "United States", "USD"),
    ("EA", "Euro Area", "EUR"),
    ("GB", "United Kingdom", "GBP"),
    ("JP", "Japan", "JPY"),
    ("CN", "China", "CNY"),
    ("CA", "Canada", "CAD"),
    ("AU", "Australia", "AUD"),
    ("CH", "Switzerland", "CHF"),
    ("SA", "Saudi Arabia", "SAR"),
    ("AE", "United Arab Emirates", "AED"),
)
_DIMENSIONS = ("growth", "inflation", "labour", "policy", "sentiment")


def country_scores() -> list[CountryScore]:
    result = []
    for code, country, currency in _COUNTRIES:
        rng = create_rng(hash_string(f"score:{code}:{AS_OF}"))
        scores = {d: max(-3, min(3, js_round(gaussian(rng) * 1.4))) for d in _DIMENSIONS}
        overall = js_to_fixed(js_sum(scores.values()) / len(_DIMENSIONS), 1)
        result.append(
            CountryScore(
                code=code,
                country=country,
                currency=currency,
                scores=CountryScores(**scores),
                overall=overall,
            )
        )
    return sorted(result, key=lambda c: -c.overall)
