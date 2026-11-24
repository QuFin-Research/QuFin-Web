"""Candidate sources: series that publish a pair another series serves (rules 37 and 38).

A candidate is loaded without being served (`staged`, Part 0) so its release timing can be measured
against the series that serves the pair, over a release cycle. It is not in the catalog: nothing
refreshes it as a served series, the API never returns it, and the duplicate check and the scorecard
leave it out. If it wins, a reviewed pull request adds it to the catalog and records the source
decision (rules 26 and 38).

The registry holds the pairs the measures still decide: the United States and every economy
Eurostat does not serve. Slice 1 staged 32 IMF consumer price series for the pairs moved to
Eurostat's HICP on 19 Nov 2026; rule 38's *Bloc aggregator first* (v3.5) makes Eurostat the source
of those pairs whatever the IMF's timing, so they were removed. Candidates are added here as other
pairs are measured.
"""

from dataclasses import dataclass

from app.data.bis_ids import MEASURES
from app.data.gap_ids import HICP_GEO
from app.data.indicator_concepts import BIS_CONCEPT, SERIES_CONCEPTS
from app.domain.source_selection import Producer

PREFIX = "CAND_"


@dataclass(frozen=True)
class Candidate:
    id: str  # CAND_<SOURCE>_<MEASURE>_<AREA>: never a catalog id
    country: str  # ISO 3166 alpha-2
    concept: str
    source: str
    producer: Producer  # how native it is for this economy (Part 0)
    area: str  # the source's own area code
    serves: str  # the series serving the pair now
    flow: str  # the source's dataset
    key: str  # the source's series key (FRED: the series id)
    months: int = 1  # months in a period: 1 monthly, 3 quarterly
    # A gap candidate has nothing to be timed against (`serves` is empty) and describes
    # itself; one that is timed copies its description from the series it serves.
    title: str = ""
    units: str = ""
    adjustment: str = ""
    dimension: str = ""
    cycle: str = ""
    frequency: str = "Monthly"
    measure: str = ""  # BIS: the measure code that says its version, units and release rule


CANDIDATES: tuple[Candidate, ...] = (
    # The United States' commercial property prices: the BIS serves the pair (provisional since
    # 19 Nov 2026); FRED's copy of the IMF's financial soundness indicator is the rival (rule 38).
    Candidate(
        id="CAND_FRED_CPP_US",
        country="US",
        concept="commercial_property_prices",
        source="fred",
        producer="bloc",
        area="US",
        serves="BIS_CPP_US",
        flow="",
        key="COMREPUSQ159N",
        months=3,
    ),
)

# FRED serves these United States series, chosen under the retired rule 17 (FRED first). The BLS is
# the original producer of each; its own series (ids checked live on 21 Nov 2026) is the candidate.
# FRED series id -> (BLS series id, months in a period).
_BLS_RIVALS: dict[str, tuple[str, int]] = {
    "PAYEMS": ("CES0000000001", 1),  # all employees, total nonfarm
    "UNRATE": ("LNS14000000", 1),  # unemployment rate
    "UEMPMEAN": ("LNS13008275", 1),  # average weeks unemployed
    "AWHMAN": ("CES3000000007", 1),  # average weekly hours, manufacturing
    "CPIAUCSL": ("CUSR0000SA0", 1),  # CPI, all items
    "CPILFESL": ("CUSR0000SA0L1E", 1),  # CPI, all items less food and energy
    "CUSR0000SAS": ("CUSR0000SAS", 1),  # CPI, services
    "PPIFIS": ("WPSFD4", 1),  # PPI, final demand
    "JTSJOL": ("JTS000000000000000JOL", 1),  # job openings
    "JTSQUR": ("JTS000000000000000QUR", 1),  # quits rate
    "ECIALLCIV": ("CIS1010000000000I", 3),  # employment cost index, civilian (quarterly)
}
CANDIDATES = (
    *CANDIDATES,
    *(
        Candidate(
            id=f"{PREFIX}BLS_{fred_id}_US",
            country="US",
            concept=SERIES_CONCEPTS[("US", fred_id)],
            source="bls",
            producer="original",
            area="US",
            serves=fred_id,
            flow="",
            key=bls_id,
            months=months,
        )
        for fred_id, (bls_id, months) in _BLS_RIVALS.items()
    ),
)

# Gaps the discovery probe found on 21 Nov 2026 (`discover`, rule 34): series a source publishes
# currently for an economy QuFin holds nothing for. Each is loaded as `staged`, never served, until
# a reviewed pull request verifies its eligibility (rules 26 and 34). Eurostat's economies are
# Eurostat's to serve (rule 38, Bloc aggregator first); the OECD fills the others.
_ESTAT_CORE: tuple[str, ...] = ()
_ESTAT_IP = ("BE",)
_OECD_CORE = {"AU": "AUS"}
_OECD_IP = {"GB": "GBR", "CA": "CAN", "IN": "IND", "MX": "MEX", "BR": "BRA", "CL": "CHL"}
_OECD_MONEY = {
    "GB": "GBR",
    "JP": "JPN",
    "CA": "CAN",
    "AU": "AUS",
    "NO": "NOR",
    "HU": "HUN",
    "ZA": "ZAF",
    "KR": "KOR",
    "IS": "ISL",
    "CO": "COL",
}


def _estat_key(geo_filters: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in geo_filters.items())


_CORE = {"freq": "M", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD"}
_IP = {"freq": "M", "indic_bt": "PRD", "nace_r2": "B-D", "s_adj": "SCA", "unit": "I21"}
_OECD_FLOW = "OECD.SDD.STES,DSD_STES@"
GAP_CANDIDATES: tuple[Candidate, ...] = (
    *(
        Candidate(
            id=f"{PREFIX}ESTAT_CORE_{iso2}",
            country=iso2,
            concept="core_consumer_prices",
            source="eurostat",
            producer="bloc",
            area=HICP_GEO[iso2],
            serves="",
            flow="prc_hicp_minr",
            key=_estat_key({**_CORE, "geo": HICP_GEO[iso2]}),
            title=f"HICP excluding energy, food, alcohol and tobacco: annual rate, {iso2}",
            units="Percentage change",
            adjustment="Not Seasonally Adjusted",
            dimension="inflation",
            cycle="lagging",
        )
        for iso2 in _ESTAT_CORE
    ),
    *(
        Candidate(
            id=f"{PREFIX}ESTAT_IP_{iso2}",
            country=iso2,
            concept="industrial_production",
            source="eurostat",
            producer="bloc",
            area=HICP_GEO[iso2],
            serves="",
            flow="sts_inpr_m",
            key=_estat_key({**_IP, "geo": HICP_GEO[iso2]}),
            title=f"Production in industry, seasonally and calendar adjusted, {iso2}",
            units="Index, 2021=100",
            adjustment="Seasonally and Calendar Adjusted",
            dimension="growth",
            cycle="coincident",
        )
        for iso2 in _ESTAT_IP
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_CORE_{iso3}",
            country=iso2,
            concept="core_consumer_prices",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow="OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,",
            key=f"{iso3}.M.N.CPI.IX._TXCP01_NRG.N._Z",
            title=f"CPI excluding food and energy, index, {iso2}",
            units="Index",
            adjustment="Not Seasonally Adjusted",
            dimension="inflation",
            cycle="lagging",
        )
        for iso2, iso3 in _OECD_CORE.items()
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_IP_{iso3}",
            country=iso2,
            concept="industrial_production",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow=f"{_OECD_FLOW}DF_INDSERV,",
            key=f"{iso3}.M.PRVM.IX.BTE.Y._Z._Z.N",
            title=f"Production volume, industry excluding construction, {iso2}",
            units="Index",
            adjustment="Seasonally Adjusted",
            dimension="growth",
            cycle="coincident",
        )
        for iso2, iso3 in _OECD_IP.items()
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_MONEY_{iso3}",
            country=iso2,
            concept="money_supply",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow=f"{_OECD_FLOW}DF_MONAGG,",
            key=f"{iso3}.M.MABM.XDC._Z.Y._Z._Z.N",
            title=f"Broad money, national currency, {iso2}",
            units="National currency",
            adjustment="Seasonally Adjusted",
            dimension="policy",
            cycle="leading",
        )
        for iso2, iso3 in _OECD_MONEY.items()
    ),
)
CANDIDATES = (*CANDIDATES, *GAP_CANDIDATES)

# Gaps the second discovery sweep found on 21 Nov 2026 (rule 34): series the BIS or the OECD
# publishes currently for an economy QuFin holds nothing for. The 98 BIS series on six served
# measures were promoted on 22 Nov 2026 (`_BATCH_A` in `bis_ids.py`); the BIS ones left here were
# held back (Russia, the United States, missing or stale periods). Batch B (22 Nov 2026) promoted
# the Eurostat core HICP (33) and industrial production (29) and the OECD survey series (10)
# (`BATCH_B_*` in `gap_ids.py`, `_OECD_BATCH_B` in `macro_catalog.py`); Belgium's production, a
# month behind, stays staged. Loaded as `staged`, never served,
# until a reviewed pull request verifies eligibility (rules 26 and 34). An economy Eurostat serves
# is left out where Eurostat also publishes the indicator (residential property prices, business
# and consumer confidence, unemployment): that is Eurostat's to serve (rule 38).
_BIS_GAP = {
    "CBPOL": ("RU",),
    "NEER": (
        "US",
        "RU",
    ),
    "REER": (
        "US",
        "RU",
    ),
    "CREDIT": (
        "US",
        "RU",
    ),
    "CREDGAP": (
        "US",
        "RU",
    ),
    "SPP": (
        "RU",
        "CL",
    ),
    "TCHH": (
        "US",
        "RU",
    ),
    "TCGOV": ("US",),
    "DSRP": (
        "US",
        "RU",
    ),
    "DSRH": ("US",),
    "DSRN": ("US",),
    "GLIUSD": ("RU",),
    "CBTA": (
        "KR",
        "ID",
        "KW",
        "IL",
    ),
    "IDS": (
        "US",
        "RU",
        "KW",
        "OM",
        "KH",
        "KE",
        "LI",
        "NG",
        "CG",
    ),
    "DSSGOV": ("US",),
    "DSSNFC": (
        "US",
        "LV",
        "LT",
    ),
    "DSSFIN": ("US",),
}
_OECD_SURVEY_GAP: dict[str, dict[str, str]] = {}
_OECD_SURVEY = {  # concept -> (OECD measure, title, dimension)
    "leading_index": ("LI", "Composite leading indicator", "growth"),
    "business_confidence": ("BCICP", "Business confidence indicator", "growth"),
    "consumer_sentiment": ("CCICP", "Consumer confidence indicator", "sentiment"),
}


def _bis_area(iso2: str) -> str:
    return "XM" if iso2 == "EA" else iso2


BIS_GAP_CANDIDATES: tuple[Candidate, ...] = tuple(
    Candidate(
        id=f"{PREFIX}BIS_{code}_{iso2}",
        country=iso2,
        concept=BIS_CONCEPT[code],
        source="bis",
        producer="global",
        area=_bis_area(iso2),
        serves="",
        flow=MEASURES[code].flow,
        key=MEASURES[code].key.format(areas=_bis_area(iso2)),
        months=1 if MEASURES[code].frequency == "Monthly" else 3,
        title=f"{MEASURES[code].title}, {iso2}",
        units=MEASURES[code].units,
        adjustment=MEASURES[code].seasonal_adjustment,
        dimension=MEASURES[code].dimension,
        cycle=MEASURES[code].cycle,
        frequency=MEASURES[code].frequency,
        measure=code,
    )
    for code, economies in _BIS_GAP.items()
    for iso2 in economies
)
OECD_SURVEY_GAP_CANDIDATES: tuple[Candidate, ...] = tuple(
    Candidate(
        id=f"{PREFIX}OECD_{measure}_{iso3}",
        country=iso2,
        concept=concept,
        source="oecd",
        producer="global",
        area=iso3,
        serves="",
        flow="OECD.SDD.STES,DSD_STES@DF_CLI,",
        key=f"{iso3}.M.{measure}.IX..AA.IX..H",
        title=f"{title} (amplitude adjusted), {iso2}",
        units="Index, long-term average = 100",
        adjustment="Amplitude Adjusted (OECD)",
        dimension=dimension,
        cycle="leading",
        measure=measure,
    )
    for concept, (measure, title, dimension) in _OECD_SURVEY.items()
    for iso2, iso3 in _OECD_SURVEY_GAP.get(concept, {}).items()
)
CANDIDATES = (*CANDIDATES, *BIS_GAP_CANDIDATES, *OECD_SURVEY_GAP_CANDIDATES)
CANDIDATE_BY_ID = {c.id: c for c in CANDIDATES}


# Trade, the current account and real GDP (probe of 21 Nov 2026, rule 34): economies QuFin holds
# nothing for. Eurostat's economies are Eurostat's where it publishes (rule 38); the OECD fills
# the others. Staged only, to be decided at the eligibility step: the OECD balances are the
# quarterly balance of payments in US dollars and Eurostat's trade balance is monthly in euro,
# unlike the monthly dollar series the trade concept holds today. The goods-and-services balance
# of Eurostat's economies waits for a Eurostat probe of it. Real GDP and the current account were
# promoted on 22 Nov 2026 for Eurostat's economies (batch C: `BATCH_C_*` in `gap_ids.py`); the
# trade balances stay here. The OECD's real GDP and current account were promoted on 22 Nov 2026
# (batch D, `OECD_FLOW_SERIES` in `gap_ids.py`).
_ESTAT_FLOWS = {
    "merchandise_trade_balance": {
        "SE": "SE",
        "DK": "DK",
        "CZ": "CZ",
        "HU": "HU",
        "PL": "PL",
        "AT": "AT",
        "BE": "BE",
        "BG": "BG",
        "HR": "HR",
        "CY": "CY",
        "EE": "EE",
        "FI": "FI",
        "GR": "EL",
        "IE": "IE",
        "LV": "LV",
        "LT": "LT",
        "LU": "LU",
        "MT": "MT",
        "NL": "NL",
        "PT": "PT",
        "RO": "RO",
        "SK": "SK",
        "SI": "SI",
        "ES": "ES",
    },
}
_OECD_FLOWS = {
    "merchandise_trade_balance": {
        "US": "USA",
        "EA": "EA",
        "NZ": "NZL",
        "CH": "CHE",
        "NO": "NOR",
        "CN": "CHN",
        "IN": "IND",
        "MX": "MEX",
        "TR": "TUR",
        "ZA": "ZAF",
        "KR": "KOR",
        "AR": "ARG",
        "ID": "IDN",
        "RU": "RUS",
        "SA": "SAU",
        "IS": "ISL",
        "IL": "ISR",
        "CL": "CHL",
        "CO": "COL",
    },
    "trade_balance": {
        "GB": "GBR",
        "JP": "JPN",
        "CA": "CAN",
        "AU": "AUS",
        "NZ": "NZL",
        "CN": "CHN",
        "IN": "IND",
        "MX": "MEX",
        "BR": "BRA",
        "ZA": "ZAF",
        "KR": "KOR",
        "AR": "ARG",
        "ID": "IDN",
        "RU": "RUS",
        "SA": "SAU",
        "CL": "CHL",
        "CO": "COL",
    },
}


def _k(*parts: str) -> str:
    return ".".join(parts)


# concept -> Eurostat (series code, dataset, filters, units, adjustment, dimension, cycle, title)
_ESTAT_FLOW_SPEC = {
    "real_gdp": (
        "GDP",
        "namq_10_gdp",
        {"freq": "Q", "unit": "CLV20_MNAC", "s_adj": "SCA", "na_item": "B1GQ"},
        "National currency, chain linked volumes (2020)",
        "Seasonally and Calendar Adjusted",
        "growth",
        "coincident",
        "Real GDP, chain linked volumes",
    ),
    "current_account_to_gdp": (
        "CA",
        "ei_bpm6ca_q",
        {
            "freq": "Q",
            "unit": "PC_GDP",
            "s_adj": "NSA",
            "sector10": "S1",
            "sectpart": "S1",
            "partner": "WRL_REST",
            "stk_flow": "BAL",
            "bop_item": "CA",
        },
        "Percent of GDP",
        "Not Seasonally Adjusted",
        "external",
        "lagging",
        "Current account balance, percent of GDP",
    ),
    "merchandise_trade_balance": (
        "TRADE",
        "ei_eteu27_2020_m",
        {
            "freq": "M",
            "stk_flow": "BAL_RT",
            "unit": "MIO-EUR-SA",
            "partner": "WORLD",
            "indic": "ET-T",
        },
        "Million euro",
        "Seasonally Adjusted",
        "external",
        "lagging",
        "Trade balance with the world",
    ),
}
# concept -> OECD (series code, flow, key template, units, dimension, cycle, title)
_OECD_BOP_FLOW = "OECD.SDD.TPS,DSD_BOP@DF_BOP,"
_OECD_FLOW_SPEC = {
    "real_gdp": (
        "GDP",
        "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_NATIO_CURR,",
        _k("Q", "Y", "{a}", "S1", "S1", "B1GQ", "", "", "", "XDC", "L", "N", ""),
        "National currency, chained volumes",
        "growth",
        "coincident",
        "Real GDP, chained volumes, seasonally adjusted",
    ),
    "current_account_to_gdp": (
        "CA",
        _OECD_BOP_FLOW,
        _k("{a}", "WXD", "CA", "B", "T", "Q", "PT_B1GQ", ""),
        "Percent of GDP",
        "external",
        "lagging",
        "Current account balance, percent of GDP",
    ),
    "merchandise_trade_balance": (
        "TRADE",
        _OECD_BOP_FLOW,
        _k("{a}", "WXD", "G", "B", "T", "Q", "USD_EXC", "N"),
        "Millions of US dollars, exchange-rate converted",
        "external",
        "lagging",
        "Balance of goods, balance of payments basis",
    ),
    "trade_balance": (
        "TRADEGS",
        _OECD_BOP_FLOW,
        _k("{a}", "WXD", "G_S", "B", "T", "Q", "USD_EXC", "N"),
        "US dollars",
        "external",
        "lagging",
        "Balance of goods and services, balance of payments basis",
    ),
}
_QUARTERLY_FLOWS = {"real_gdp", "current_account_to_gdp"}

FLOW_GAP_CANDIDATES: tuple[Candidate, ...] = (
    *(
        Candidate(
            id=f"{PREFIX}ESTAT_{code}_{iso2}",
            country=iso2,
            concept=concept,
            source="eurostat",
            producer="bloc",
            area=geo,
            serves="",
            flow=dataset,
            key=_estat_key({**filters, "geo": geo}),
            months=3 if concept in _QUARTERLY_FLOWS else 1,
            title=f"{title}, {iso2}",
            units=units,
            adjustment=adjustment,
            dimension=dimension,
            cycle=cycle,
            frequency="Quarterly" if concept in _QUARTERLY_FLOWS else "Monthly",
        )
        for concept, economies in _ESTAT_FLOWS.items()
        for code, dataset, filters, units, adjustment, dimension, cycle, title in [
            _ESTAT_FLOW_SPEC[concept]
        ]
        for iso2, geo in economies.items()
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_{code}_{area}",
            country=iso2,
            concept=concept,
            source="oecd",
            producer="global",
            area=area,
            serves="",
            flow=flow,
            key=key.format(a=area),
            months=3,
            title=f"{title}, {iso2}",
            units=units,
            adjustment="As published by the OECD",
            dimension=dimension,
            cycle=cycle,
            frequency="Quarterly",
        )
        for concept, economies in _OECD_FLOWS.items()
        for code, flow, key, units, dimension, cycle, title in [_OECD_FLOW_SPEC[concept]]
        for iso2, area in economies.items()
    ),
)
CANDIDATES = (*CANDIDATES, *FLOW_GAP_CANDIDATES)
CANDIDATE_BY_ID = {c.id: c for c in CANDIDATES}
