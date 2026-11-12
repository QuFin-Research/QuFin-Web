"""Macro series QuFin tracks, grouped by the scorecard dimension each one informs.

US first (FRED/ALFRED); other economies follow as their sources are connected.

Business-cycle timing follows the Conference Board's leading, coincident and lagging indexes,
using the published components (or the closest public series where a component is
proprietary: ISM new orders -> Philadelphia Fed new orders, the Leading Credit Index -> the
Chicago Fed's financial conditions index). The S&P 500 component is left to a price source:
FRED keeps only ten years of it and no vintages.
"""

from dataclasses import dataclass, replace
from datetime import date
from typing import Literal

from app.data.bis_ids import BIS_COUNTRIES, BIS_SERIES, MEASURES
from app.data.cycle_classification import QUFIN_CYCLE
from app.data.gap_ids import (
    EURO_MEMBERS,
    FRED_ADDITIONS,
    HISTORY_START,
    KUWAIT_POLICY,
    ONS_COUNTRY,
    ONS_SERIES,
)
from app.data.macro_ids import IMF_CPI, MACRO_COUNTRY, OECD_MACRO
from app.data.reserves_ids import FRED_RESERVES, RESERVES

# The five scored pillars, plus external and fiscal (stored and shown; scored once the
# scorecard moves to eight pillars, ADR 0005) and markets (reference prices, never scored).
Dimension = Literal[
    "growth",
    "inflation",
    "labour",
    "policy",
    "sentiment",
    "external",
    "fiscal",
    "energy",
    "markets",
    "housing",
]
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
    source: Literal["bis", "bls", "eia", "ecb", "fred", "imf", "oecd", "ons", "treasury"]
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
    # Rule I: the first observation to load when the caller asks for the default start.
    history_start: date | None = None


def start_for(series_id: str, requested: date) -> date:
    """The start a job should use: the series' own deeper history unless a start was given."""
    entry = BY_ID.get(series_id)
    if entry is not None and entry.history_start and requested == DEFAULT_OBSERVATION_START:
        return entry.history_start
    return requested


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
        "GACDISA066MSFRBNY",
        "BACTSAMFRBDAL",
        "T10YFF",
        "T10Y3M",
        "NFCI",
        "STLFSI4",
        "UMCSENT",
        "UEMPMEAN",
        "UNRATE",
        "ISRATIO",
        "T10YIE",
        "FEDFUNDS",
        "DGS2",
        "JTSQUR",
        "BOPGSTB",
        "IEABC",
        "MTSDS133FMS",
        "GFDEGDQ188S",
        "WPULEUS3",
        "USALOLITOAASTSAM",
        "FM.D.U2.EUR.4F.KR.DFR.LEV",
        "TREAS_AVG_RATE_MARKETABLE",
        "DFII10",
        "BAA10Y",
    }
)


def _eia(id: str) -> CatalogSeries:
    """A Weekly Petroleum Status Report series, from the EIA API (not on FRED)."""
    return CatalogSeries(id, "eia", "US", "energy", change="diff" if id in DIFF_SERIES else "pct")


def _ea(id: str, dimension: Dimension, *, published_as_change: bool = False) -> CatalogSeries:
    """A euro area series from the ECB Data Portal; id = dataflow + "." + series key.

    Not scored: the scorecard does not mix countries until each has its own verified set.
    """
    return CatalogSeries(
        id,
        "ecb",
        "EA",
        dimension,
        change="diff" if published_as_change or id in DIFF_SERIES else "pct",
        published_as_change=published_as_change,
    )


def _treasury(id: str) -> CatalogSeries:
    """A Treasury Fiscal Data series (Bureau of the Fiscal Service), not on FRED."""
    return CatalogSeries(
        id, "treasury", "US", "fiscal", change="diff" if id in DIFF_SERIES else "pct"
    )


def _bls(id: str) -> CatalogSeries:
    """A BLS series (Bureau of Labor Statistics), not on FRED (rule 17)."""
    return CatalogSeries(id, "bls", "US", "external", change="diff" if id in DIFF_SERIES else "pct")


# OECD composite leading indicators and confidence surveys for the OECD members among QuFin's
# economies, each checked live one series at a time on 6 Nov 2026 (latest month August or
# September 2026). Left out: leading indicators the OECD does not publish (New Zealand,
# Switzerland, Norway, Sweden, Denmark, Czechia, Hungary, Poland); Canadian and Norwegian
# business confidence (last April and June 2026: behind schedule); Norwegian consumer
# confidence (not published). Consumer confidence for Switzerland, Sweden, Denmark, Czechia,
# Hungary and Korea was verified live on 7 Nov 2026. US business and consumer confidence are
# left out: the OECD builds them from ISM and Michigan data (licence limits), and Michigan
# sentiment is already stored (rule 16). The US leading indicator comes from FRED, which
# carries it live with vintages (rule 17).
_OECD_ISO2 = {
    "DEU": "DE",
    "FRA": "FR",
    "ITA": "IT",
    "GBR": "GB",
    "JPN": "JP",
    "CAN": "CA",
    "AUS": "AU",
    "MEX": "MX",
    "TUR": "TR",
    "KOR": "KR",
    "NZL": "NZ",
    "CHE": "CH",
    "SWE": "SE",
    "DNK": "DK",
    "CZE": "CZ",
    "HUN": "HU",
    "POL": "PL",
}
_OECD_LIVE = {
    "LI": ("GBR", "JPN", "CAN", "AUS", "MEX", "TUR", "KOR", "DEU", "FRA", "ITA"),
    "BCICP": (
        "DEU",
        "FRA",
        "ITA",
        "GBR",
        "JPN",
        "AUS",
        "NZL",
        "CHE",
        "SWE",
        "DNK",
        "CZE",
        "HUN",
        "POL",
        "MEX",
        "TUR",
        "KOR",
    ),
    "CCICP": (
        "DEU",
        "FRA",
        "ITA",
        "GBR",
        "JPN",
        "CAN",
        "AUS",
        "NZL",
        "POL",
        "MEX",
        "TUR",
        "CHE",
        "SWE",
        "DNK",
        "CZE",
        "HUN",
        "KOR",
    ),
}
_OECD_DIMENSION: dict[str, Dimension] = {"LI": "growth", "BCICP": "growth", "CCICP": "sentiment"}
_OECD_ID = {"LI": "CLI", "BCICP": "BCI", "CCICP": "CCI"}

# Catalog id -> (OECD area, measure).
OECD_SERIES: dict[str, tuple[str, str]] = {
    f"OECD_{_OECD_ID[measure]}_{area}": (area, measure)
    for measure, areas in _OECD_LIVE.items()
    for area in areas
}


def _oecd(series_id: str) -> CatalogSeries:
    """An OECD index (long-term average 100): leading, changes in points, not scored."""
    area, measure = OECD_SERIES[series_id]
    return CatalogSeries(
        series_id, "oecd", _OECD_ISO2[area], _OECD_DIMENSION[measure], "leading", change="diff"
    )


_BIS_LICENCE = (
    "BIS statistics may be used if the BIS is cited as the source, the use is not misleading "
    "or implying endorsement, and their inclusion in a commercial product adds no charge for "
    "users (https://data.bis.org/help/legal)."
)


def _bis(series_id: str) -> CatalogSeries:
    """A BIS series (policy rate, effective exchange rate, credit), not scored.

    FRED's copies of some of these lag the BIS API by months, so the API is read directly.
    """
    measure = MEASURES[BIS_SERIES[series_id][0]]
    return CatalogSeries(
        series_id,
        "bis",
        BIS_COUNTRIES[series_id],
        measure.dimension,
        change=measure.change,
        licence_note=_BIS_LICENCE,
    )


def _oecd_unemployment(series_id: str) -> CatalogSeries:
    """Unemployment rate, percent of the labour force (OECD, ILO definition); change in points."""
    return CatalogSeries(series_id, "oecd", MACRO_COUNTRY[series_id], "labour", change="diff")


def _imf_cpi(series_id: str) -> CatalogSeries:
    """Consumer prices as the IMF publishes them: the annual rate of change, never changed again."""
    return CatalogSeries(
        series_id,
        "imf",
        MACRO_COUNTRY[series_id],
        "inflation",
        change="diff",
        published_as_change=True,
    )


def _reserves(series_id: str) -> CatalogSeries:
    """Reserves excluding gold: an amount in US dollars (percent change), not scored."""
    if series_id in FRED_RESERVES:
        return CatalogSeries(series_id, "fred", RESERVES[series_id], "external")
    return CatalogSeries(series_id, "imf", RESERVES[series_id], "external")


_H15 = "Board of Governors of the Federal Reserve System (H.15); spread calculated by FRED"


_DECLARED: tuple[CatalogSeries, ...] = (
    # --- Leading: turn before the economy ------------------------------------------------
    _us("AWHMAN", "labour", "leading"),  # Average weekly hours, manufacturing
    _us("ICSA", "labour", "leading"),  # Initial jobless claims, weekly
    _us("ACOGNO", "growth", "leading"),  # New orders, consumer goods
    _us("NEWORDER", "growth", "leading"),  # New orders, core capital goods
    _us("NOCDFSA066MSFRBPHI", "growth", "leading"),  # Philadelphia Fed new orders
    # Regional Fed manufacturing surveys: one series per survey (rule 16), the headline index
    # where Philadelphia is not already read through new orders. Not scored until verified
    # under rule 10. Richmond and Kansas City publish theirs off FRED (gap, not loaded).
    _us("GACDISA066MSFRBNY", "growth", "leading"),  # Empire State general business conditions
    _us("BACTSAMFRBDAL", "growth", "leading"),  # Dallas Fed Texas general business activity
    _us("PERMIT", "growth", "leading"),  # Building permits
    _us("HOUST", "growth", "leading"),  # Housing starts
    _us("HSN1F", "growth", "leading"),  # New single-family home sales
    _us("TEMPHELPS", "labour", "leading"),  # Temporary help services employment
    _us("JTSJOL", "labour", "leading"),  # JOLTS job openings
    _us("JTSQUR", "labour", "leading"),  # JOLTS quits rate
    _us("T10YFF", "policy", "leading", market=True, source=_H15),  # 10-year yield minus fed funds
    _us("T10Y3M", "policy", "leading", market=True, source=_H15),  # 10-year minus 3-month yield
    _us("NFCI", "sentiment", "leading"),  # Chicago Fed financial conditions, weekly
    _us("STLFSI4", "sentiment", "leading"),  # St. Louis Fed financial stress, weekly
    _us("USALOLITOAASTSAM", "growth", "leading", source="OECD"),  # OECD US leading indicator
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
    _us("PCEC96", "growth", "coincident"),  # Real personal consumption expenditures
    _us("PI", "growth", "coincident"),  # Personal income, nominal (not scored)
    _us("PAYEMS", "labour", "coincident"),  # Nonfarm payrolls
    # --- Lagging: turn after the economy -------------------------------------------------
    _us("UEMPMEAN", "labour", "lagging"),  # Average weeks unemployed
    _us("UNRATE", "labour", "lagging"),  # Unemployment rate
    _us("CCSA", "labour", "lagging"),  # Continued claims (insured unemployment), weekly
    _us("ISRATIO", "growth", "lagging"),  # Business inventories to sales
    _us("ULCMFG", "inflation", "lagging"),  # Unit labour costs, manufacturing, quarterly
    _us("CUSR0000SAS", "inflation", "lagging"),  # CPI, services
    _us("CPILFESL", "inflation", "lagging"),  # Core CPI
    _us("BUSLOANS", "policy", "lagging"),  # Commercial and industrial loans
    _us("TOTALSL", "policy", "lagging"),  # Consumer credit outstanding
    # --- Not classified by cycle -----------------------------------------------------------
    _us("CPIAUCSL", "inflation", "lagging"),  # CPI, all items: prices follow the cycle
    _us("GASREGW", "inflation"),  # Retail gasoline price, weekly (EIA)
    _us("PCEPILFE", "inflation"),  # Core PCE price index
    _us("PPIFIS", "inflation"),  # Producer prices, final demand
    _us("CP", "growth"),  # Corporate profits after tax, quarterly (nominal, not scored)
    _us("T10YIE", "inflation", market=True, source=_H15),  # 10-year breakeven inflation
    _us("FEDFUNDS", "policy"),  # Effective fed funds rate
    _us("DGS2", "policy", market=True),  # 2-year Treasury yield
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
    # --- External and fiscal: mandatory to gauge a currency; scored with eight pillars ------
    _us("BOPGSTB", "external"),  # Trade balance, goods and services
    _us("IEABC", "external"),  # Current account balance, quarterly
    _us("MTSDS133FMS", "fiscal"),  # Federal surplus or deficit, monthly
    _us("GFDEGDQ188S", "fiscal"),  # Federal debt as % of GDP, quarterly
    _treasury("TREAS_DEBT_TOTAL"),  # Debt to the Penny: total public debt, daily
    _treasury("TREAS_AVG_RATE_MARKETABLE"),  # Average rate on marketable debt, monthly
    _treasury("TREAS_INTEREST_EXPENSE"),  # Interest expense on the public debt, monthly
    # --- Employment Cost Index (P1-12): FRED carries it SA with vintages, so it is the single
    # source (rule 17, Rule H); the BLS copy CIS1010000000000I was removed as a duplicate. ---
    _us("ECIALLCIV", "labour"),  # ECI, total compensation, civilian workers
    # --- Energy: EIA Weekly Petroleum Status Report (not on FRED), not scored -------------
    _eia("WCESTUS1"),  # Crude oil stocks excluding SPR
    _eia("W_EPC0_SAX_YCUOK_MBBL"),  # Cushing, OK crude stocks
    _eia("WCSSTUS1"),  # Strategic Petroleum Reserve
    _eia("WCRFPUS2"),  # Crude oil field production
    _eia("WPULEUS3"),  # Refinery utilisation
    _eia("WGTSTUS1"),  # Total gasoline stocks
    _eia("WDISTUS1"),  # Distillate fuel oil stocks
    _eia("WCRIMUS2"),  # Crude oil imports
    _eia("WCREXUS2"),  # Crude oil exports
    _eia("WRPUPUS2"),  # Product supplied, all petroleum products
    _eia("WGFUPUS2"),  # Product supplied, finished motor gasoline
    _eia("WDIUPUS2"),  # Product supplied, distillate fuel oil
    # --- Euro area: ECB Data Portal (P1-19), not scored ---------------------------------
    # ECB euro reference FX rates are not loaded: EUR/USD is already stored from Fed H.10
    # (DEXUSEU), and a second fixing of the same rate would be duplicated data (rule 16).
    _ea("FM.D.U2.EUR.4F.KR.DFR.LEV", "policy"),  # Deposit facility rate, daily
    _ea("HICP.M.U2.N.000000.4D0.ANR", "inflation", published_as_change=True),  # HICP, y/y
    _ea("HICP.M.U2.N.XEF000.4D0.ANR", "inflation", published_as_change=True),  # Core HICP, y/y
    _ea("BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E", "policy"),  # M3 money supply, stock, SA
    # --- Official reserves excluding gold (P1-21), not scored -----------------------------
    *(_reserves(series_id) for series_id in RESERVES),
    # --- BIS: policy rates, effective exchange rates, credit-to-GDP (P1-22), not scored
    *(_bis(series_id) for series_id in BIS_SERIES),
    # --- OECD leading indicators and confidence (P1-20), not scored -------------------
    *(_oecd(series_id) for series_id in OECD_SERIES),
    # --- Consumer prices and unemployment for the comparison view (P1-23), not scored -----
    *(_imf_cpi(series_id) for series_id in IMF_CPI),
    *(_oecd_unemployment(series_id) for series_id in OECD_MACRO),
    # --- Coverage gaps (Sprints 1-4): FRED for other economies, ONS for the UK (Rule H), each
    # loaded from 1990 where the source goes back that far (Rule I) --------------------------
    *(
        CatalogSeries(
            a.id,
            "fred",
            a.country,
            a.dimension,
            a.cycle,
            change=a.change,
            history_start=HISTORY_START,
        )
        for a in FRED_ADDITIONS
    ),
    *(
        CatalogSeries(
            s.id,
            "ons",
            ONS_COUNTRY,
            s.dimension,
            s.cycle,
            change=s.change,
            published_as_change=s.published_as_change,
            history_start=HISTORY_START,
        )
        for s in ONS_SERIES
    ),
    # --- Markets: daily reference prices (P1-25), not scored ---------------------------
    # Fed H.10 noon buying rates in New York (public domain), quoted as the market quotes the
    # pair; published weekly for the previous week.
    _us("DEXUSEU", "markets", market=True),  # EURUSD
    _us("DEXUSUK", "markets", market=True),  # GBPUSD
    _us("DEXJPUS", "markets", market=True),  # USDJPY
    _us("DEXUSAL", "markets", market=True),  # AUDUSD
    _us("DEXUSNZ", "markets", market=True),  # NZDUSD
    _us("DEXCAUS", "markets", market=True),  # USDCAD
    _us("DEXSZUS", "markets", market=True),  # USDCHF
    # EIA spot prices (public domain).
    _us("DCOILWTICO", "markets", market=True),  # WTI, Cushing
    _us("DCOILBRENTEU", "markets", market=True),  # Brent, Europe
    _us("DHHNGSP", "markets", market=True),  # Henry Hub natural gas
    # Not on FRED, or not allowed: gold and silver (LBMA withdrawn from FRED, licensed source
    # needed); bitcoin and ether (Coinbase forbids reproduction without written permission).
    # Broad dollar index; reweighted in 2019 and 2021, so point in time only from 2019.
    _us("DTWEXBGS", "sentiment"),
)


# Series added by the coverage-gap sprints that come from a source whose catalog helper does not
# set the start itself: they load from 1990 too (Rule I). Series stored before keep their start.
_DEEP_HISTORY: frozenset[str] = frozenset(
    {
        sid
        for sid, (code, area) in BIS_SERIES.items()
        if code == "SPP" or area in EURO_MEMBERS or (code == "CBPOL" and area == KUWAIT_POLICY)
    }
    | {
        f"OECD_{_OECD_ID[m]}_{a}"
        for m in _OECD_LIVE
        for a in _OECD_LIVE[m]
        if a in ("DEU", "FRA", "ITA")
    }
    | {"IMF_RES_KWT", "IMF_RES_QAT"}
)


def _with_cycle(series: CatalogSeries) -> CatalogSeries:
    """Every series has a cycle: the Conference Board's where it is an index component, else
    QuFin's classification (cycle_classification.py). A series with neither fails to load."""
    if series.id in _DEEP_HISTORY:
        series = replace(series, history_start=HISTORY_START)
    if series.cycle is not None:
        return series
    if series.id not in QUFIN_CYCLE:
        raise ValueError(
            f"{series.id} has no business-cycle classification: add it to "
            "app/data/cycle_classification.py with the reason"
        )
    return replace(series, cycle=QUFIN_CYCLE[series.id][0])


CATALOG: tuple[CatalogSeries, ...] = tuple(_with_cycle(s) for s in _DECLARED)

BY_ID = {s.id: s for s in CATALOG}
