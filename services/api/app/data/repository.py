"""Market data access layer.

Routes and domain code depend only on the `MarketRepository` protocol. Today it is backed by
the deterministic sample generator; real connectors (FRED/ALFRED with point-in-time vintages,
CFTC COT, EIA, price vendors) and the model service plug in by implementing the same protocol
and being returned from `get_market_repository`.
"""

from collections.abc import Sequence
from typing import Protocol

from app.data import sample
from app.schemas.base import DataOrigin
from app.schemas.market import Asset, Candle, CountryScore, Signal, SignalDriver


class MarketRepository(Protocol):
    as_of: str
    # "sample" until real prices and a validated signal model replace the generator.
    origin: DataOrigin

    def list_assets(self) -> list[Asset]: ...

    def get_asset(self, symbol: str) -> Asset | None: ...

    def get_candles(self, symbol: str) -> Sequence[Candle]: ...

    def get_signals(self, symbol: str) -> Sequence[Signal]: ...

    def get_drivers(self, asset: Asset, signal: Signal) -> list[SignalDriver]: ...

    def get_country_scores(self) -> list[CountryScore]: ...


class SampleMarketRepository:
    """Serves the same deterministic data as the web app's offline mock."""

    as_of = sample.AS_OF
    origin: DataOrigin = "sample"

    def list_assets(self) -> list[Asset]:
        return [spec.to_asset() for spec in sample.ASSETS]

    def get_asset(self, symbol: str) -> Asset | None:
        spec = sample.get_spec(symbol)
        return spec.to_asset() if spec else None

    def get_candles(self, symbol: str) -> Sequence[Candle]:
        series = sample.get_series(symbol)
        return series.candles if series else ()

    def get_signals(self, symbol: str) -> Sequence[Signal]:
        series = sample.get_series(symbol)
        return series.signals if series else ()

    def get_drivers(self, asset: Asset, signal: Signal) -> list[SignalDriver]:
        return sample.drivers_for(asset, signal)

    def get_country_scores(self) -> list[CountryScore]:
        return sample.country_scores()


_repository = SampleMarketRepository()


def get_market_repository() -> MarketRepository:
    """FastAPI dependency; override in tests or swap for a real connector."""
    return _repository
