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


CATALOG: tuple[CatalogSeries, ...] = (
    CatalogSeries("GDPC1", "fred", "US", "growth"),  # Real GDP, quarterly
    CatalogSeries("INDPRO", "fred", "US", "growth"),  # Industrial production
    CatalogSeries("CPIAUCSL", "fred", "US", "inflation"),  # CPI, all items
    CatalogSeries("PCEPILFE", "fred", "US", "inflation"),  # Core PCE price index
    CatalogSeries("UNRATE", "fred", "US", "labour"),  # Unemployment rate
    CatalogSeries("PAYEMS", "fred", "US", "labour"),  # Nonfarm payrolls
    CatalogSeries("FEDFUNDS", "fred", "US", "policy"),  # Effective fed funds rate
    CatalogSeries("DGS2", "fred", "US", "policy"),  # 2-year Treasury yield
    CatalogSeries("UMCSENT", "fred", "US", "sentiment"),  # Michigan consumer sentiment
)

BY_ID = {s.id: s for s in CATALOG}
