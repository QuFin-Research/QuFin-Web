"""Macro series QuFin tracks, grouped by the scorecard dimension each one informs.

US first (FRED/ALFRED); other economies follow as their sources are connected.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Dimension = Literal["growth", "inflation", "labour", "policy", "sentiment"]

# Enough history for the walk-forward windows without pulling every vintage since 1939.
DEFAULT_OBSERVATION_START = date(2000, 1, 1)


@dataclass(frozen=True)
class CatalogSeries:
    id: str
    source: Literal["fred"]
    country: str
    dimension: Dimension
    # Market rates are not revised beyond rare error corrections, so periods from before
    # ALFRED started archiving the series can be dated by their usual release lag instead
    # of being dropped. Not for series that get rebased or reweighted.
    market: bool = False


CATALOG: tuple[CatalogSeries, ...] = (
    # Growth
    CatalogSeries("GDPC1", "fred", "US", "growth"),  # Real GDP, quarterly
    CatalogSeries("INDPRO", "fred", "US", "growth"),  # Industrial production
    CatalogSeries("RSAFS", "fred", "US", "growth"),  # Retail sales
    # Inflation
    CatalogSeries("CPIAUCSL", "fred", "US", "inflation"),  # CPI, all items
    CatalogSeries("PCEPILFE", "fred", "US", "inflation"),  # Core PCE price index
    CatalogSeries("T10YIE", "fred", "US", "inflation", market=True),  # 10y breakeven inflation
    # Labour
    CatalogSeries("UNRATE", "fred", "US", "labour"),  # Unemployment rate
    CatalogSeries("PAYEMS", "fred", "US", "labour"),  # Nonfarm payrolls
    CatalogSeries("ICSA", "fred", "US", "labour"),  # Initial jobless claims, weekly
    # Policy, rates and liquidity
    CatalogSeries("FEDFUNDS", "fred", "US", "policy"),  # Effective fed funds rate
    CatalogSeries("DGS2", "fred", "US", "policy", market=True),  # 2-year Treasury yield
    CatalogSeries("DGS10", "fred", "US", "policy", market=True),  # 10-year Treasury yield
    CatalogSeries("DFII10", "fred", "US", "policy", market=True),  # 10-year real (TIPS) yield
    CatalogSeries("WALCL", "fred", "US", "policy", market=True),  # Fed balance sheet, weekly
    CatalogSeries("M2SL", "fred", "US", "policy"),  # M2 money supply
    # Sentiment and financial conditions
    CatalogSeries("UMCSENT", "fred", "US", "sentiment"),  # Michigan consumer sentiment
    CatalogSeries("BAA10Y", "fred", "US", "sentiment", market=True),  # Baa credit spread
    # Broad dollar index; reweighted in 2019 and 2021, so point in time only from 2019.
    CatalogSeries("DTWEXBGS", "fred", "US", "sentiment"),
)

BY_ID = {s.id: s for s in CATALOG}
