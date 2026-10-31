"""Macro series QuFin tracks, grouped by the scorecard dimension each one informs.

US first (FRED/ALFRED); other economies follow as their sources are connected.

Business-cycle timing follows the Conference Board's leading, coincident and lagging indexes,
using the published components (or the closest public series where a component is
proprietary: ISM new orders -> Philadelphia Fed new orders, the Leading Credit Index -> the
Chicago Fed's financial conditions index). The S&P 500 component is left to a price source:
FRED keeps only ten years of it and no vintages.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Dimension = Literal["growth", "inflation", "labour", "policy", "sentiment"]
Cycle = Literal["leading", "coincident", "lagging"]
# How a change is measured. pct: percent change, for quantities and price indexes. diff:
# change in the series' own units (percentage points, index points), for rates, spreads,
# ratios and indexes that can be zero or negative; a percent change of those misleads.
ChangeKind = Literal["pct", "diff"]

# Enough history for the walk-forward windows without pulling every vintage since 1939.
DEFAULT_OBSERVATION_START = date(2000, 1, 1)


@dataclass(frozen=True)
class CatalogSeries:
    id: str
    source: Literal["fred"]
    country: str
    dimension: Dimension
    cycle: Cycle | None = None
    # Days FRED publishes after the source does (licensing). Must match FRED's own delay
    # notice: a notice without a declared delay fails the release check until reviewed.
    fred_delay_days: int = 0
    delay_note: str | None = None
    # For series FRED derives itself (spreads), the agencies whose data it uses; FRED's own
    # metadata would otherwise name the St. Louis Fed as the source.
    source_override: str | None = None
    # Limits on commercial use set by the producer, whatever channel the data arrives through.
    licence_note: str | None = None
    # Market rates are not revised beyond rare error corrections, so periods from before
    # ALFRED started archiving the series can be dated by their usual release lag instead
    # of being dropped. Not for series that get rebased or reweighted.
    market: bool = False
    # Set from the series' definition, never assumed. See DIFF_SERIES below.
    change: ChangeKind = "pct"
    # The source already publishes it as a change or growth rate (e.g. WEI is scaled to GDP
    # growth): taking a change again would be a change of a change. Forces `change="diff"`,
    # and the release check fails if a percent change or y/y transform is configured for it.
    published_as_change: bool = False


def _us(
    id: str,
    dimension: Dimension,
    cycle: Cycle | None = None,
    *,
    market: bool = False,
    source: str | None = None,
    licence: str | None = None,
    published_as_change: bool = False,
) -> CatalogSeries:
    return CatalogSeries(
        id,
        "fred",
        "US",
        dimension,
        cycle,
        market=market,
        source_override=source,
        licence_note=licence,
        change="diff" if published_as_change or id in DIFF_SERIES else "pct",
        published_as_change=published_as_change,
    )


# Rates, spreads, ratios, hours, weeks, surveys and diffusion or conditions indexes: their
# change is measured in their own units. Everything else is a quantity or price index.
DIFF_SERIES = frozenset(
    {
        "AWHMAN",
        "NOCDFSA066MSFRBPHI",
        "T10YFF",
        "T10Y3M",
        "T10Y2Y",
        "NFCI",
        "STLFSI4",
        "UMCSENT",
        "UEMPMEAN",
        "UNRATE",
        "ISRATIO",
        "MPRIME",
        "T10YIE",
        "FEDFUNDS",
        "DGS2",
        "DGS10",
        "DFII10",
        "BAA10Y",
    }
)

_H15 = "Board of Governors of the Federal Reserve System (H.15); spread calculated by FRED"


CATALOG: tuple[CatalogSeries, ...] = (
    # --- Leading: turn before the economy ------------------------------------------------
    _us("AWHMAN", "labour", "leading"),  # Average weekly hours, manufacturing
    _us("ICSA", "labour", "leading"),  # Initial jobless claims, weekly
    _us("ACOGNO", "growth", "leading"),  # New orders, consumer goods
    _us("NEWORDER", "growth", "leading"),  # New orders, core capital goods
    _us("NOCDFSA066MSFRBPHI", "growth", "leading"),  # Philadelphia Fed new orders
    _us("PERMIT", "growth", "leading"),  # Building permits
    _us("HOUST", "growth", "leading"),  # Housing starts
    _us("T10YFF", "policy", "leading", market=True, source=_H15),  # 10-year yield minus fed funds
    _us("T10Y3M", "policy", "leading", market=True, source=_H15),  # 10-year minus 3-month yield
    _us("T10Y2Y", "policy", "leading", market=True, source=_H15),  # 10-year minus 2-year
    _us("NFCI", "sentiment", "leading"),  # Chicago Fed financial conditions, weekly
    _us("STLFSI4", "sentiment", "leading"),  # St. Louis Fed financial stress, weekly
    CatalogSeries(
        "UMCSENT",  # Michigan consumer sentiment
        "fred",
        "US",
        "sentiment",
        "leading",
        fred_delay_days=30,
        delay_note=(
            "At the University of Michigan's request FRED shows this survey one month after "
            "Michigan publishes it, and only the final monthly reading (Michigan also "
            "publishes a preliminary one mid-month)."
        ),
        licence_note=(
            "Free for research or strictly internal use only (CC-BY-NC-ND). Use in a product "
            "sold to others, or redistribution via a platform, dashboard or investment "
            "advisory, needs a licence from umsurvey@umich.edu "
            "(https://data.sca.isr.umich.edu/agreement.php)."
        ),
    ),
    # --- Coincident: move with the economy -----------------------------------------------
    _us("GDPC1", "growth", "coincident"),  # Real GDP, quarterly
    # NY Fed Weekly Economic Index: scaled to four-quarter GDP growth, so already a growth rate.
    _us("WEI", "growth", "coincident", published_as_change=True),
    _us("INDPRO", "growth", "coincident"),  # Industrial production
    _us("RRSFS", "growth", "coincident"),  # Real retail sales (CPI-adjusted)
    _us("W875RX1", "growth", "coincident"),  # Real personal income less transfers
    # Nominal versions keep their timing tag; only the real versions are scored.
    _us("RSAFS", "growth", "coincident"),  # Retail sales, nominal
    _us("PI", "growth", "coincident"),  # Personal income, nominal
    _us("PAYEMS", "labour", "coincident"),  # Nonfarm payrolls
    # --- Lagging: turn after the economy -------------------------------------------------
    _us("UEMPMEAN", "labour", "lagging"),  # Average weeks unemployed
    _us("UNRATE", "labour", "lagging"),  # Unemployment rate
    _us("CCSA", "labour", "lagging"),  # Continued claims (insured unemployment), weekly
    _us("ISRATIO", "growth", "lagging"),  # Business inventories to sales
    _us("ULCMFG", "inflation", "lagging"),  # Unit labour costs, manufacturing, quarterly
    _us("CUSR0000SAS", "inflation", "lagging"),  # CPI, services
    _us("CPILFESL", "inflation", "lagging"),  # Core CPI
    _us("MPRIME", "policy", "lagging"),  # Bank prime loan rate
    _us("BUSLOANS", "policy", "lagging"),  # Commercial and industrial loans
    _us("TOTALSL", "policy", "lagging"),  # Consumer credit outstanding
    # --- Not classified by cycle -----------------------------------------------------------
    _us("CPIAUCSL", "inflation"),  # CPI, all items
    _us("GASREGW", "inflation"),  # Retail gasoline price, weekly (EIA)
    _us("PCEPILFE", "inflation"),  # Core PCE price index
    _us("T10YIE", "inflation", market=True, source=_H15),  # 10-year breakeven inflation
    _us("FEDFUNDS", "policy"),  # Effective fed funds rate
    _us("DGS2", "policy", market=True),  # 2-year Treasury yield
    _us("DGS10", "policy", market=True),  # 10-year Treasury yield
    _us("DFII10", "policy", market=True),  # 10-year real (TIPS) yield
    _us("WALCL", "policy", market=True),  # Fed balance sheet, weekly
    _us("M2SL", "policy"),  # M2 money supply
    _us(
        "BAA10Y",
        "sentiment",
        market=True,
        source="Moody's (Baa yield) and Federal Reserve H.15; spread calculated by FRED",
        licence=(
            "Moody's states its data is proprietary and licensed; confirm terms before "
            "redistributing it in a commercial product."
        ),
    ),  # Baa credit spread
    # Broad dollar index; reweighted in 2019 and 2021, so point in time only from 2019.
    _us("DTWEXBGS", "sentiment"),
)

BY_ID = {s.id: s for s in CATALOG}
