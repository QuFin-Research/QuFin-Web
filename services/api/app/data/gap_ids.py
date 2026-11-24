"""Series added to close coverage gaps (Sprints 1-4 of the v3 workbook), each checked at its source.

Checked live on 13 Nov 2026. What was added, and what was left out and why:

- FRED/ALFRED (old rule H, not re-measured under rule 38): real GDP for Germany, France, Italy,
  Japan and Canada, and the goods trade
  balance of five economies (the UK is left out: its series fell overdue on 13 Nov 2026, because
  FRED posts the OECD's UK figures every second month), all seasonally adjusted with vintages.
  Left out because FRED's copy is frozen: industrial production (`*PROINDMISMEI`, last March
  2024) and core CPI (`*CPICORMINMEI`,
  last March 2025 or June 2021), the OECD's MEI series that FRED no longer updates; the UK real GDP
  series `CLVMNACSCAB1GQUK` (marked DISCONTINUED, last July 2020); and the Brazilian and South
  African unemployment series (`LRHUTTTT{BR,ZA}M156S` do not exist on FRED).
- ONS (the original producer, rule 38; old rule H, UK fallback): unemployment rate, real GDP and
  core CPI, where FRED has no current
  seasonally adjusted series with vintages. The ONS publishes the latest values only, so each period
  is dated by its usual release lag, erring late (rule 9).
- Every series here starts in 1990 where the source goes back that far (Rule 33).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

HISTORY_START = date(1990, 1, 1)  # Rule 33: the training horizon for every series added from now on


@dataclass(frozen=True)
class FredAddition:
    id: str
    country: str  # ISO2
    dimension: Literal["growth", "external", "labour", "inflation"]
    concept: str
    unit_kind: str
    currency: str | None
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]


_GDP_REASON = "Output is the cycle itself: real GDP moves with it."
_TRADE_REASON = "Trade balances adjust after the cycle has turned."

FRED_ADDITIONS: tuple[FredAddition, ...] = (
    *(
        FredAddition(
            sid,
            iso2,
            "growth",
            "real_gdp",
            "amount_currency",
            ccy,
            "coincident",
            _GDP_REASON,
            "pct",
        )
        for sid, iso2, ccy in (
            ("CLVMNACSCAB1GQDE", "DE", "EUR"),  # Millions of Chained 2010 Euros
            ("CLVMNACSCAB1GQFR", "FR", "EUR"),
            ("CLVMNACSCAB1GQIT", "IT", "EUR"),
            ("JPNRGDPEXP", "JP", "JPY"),  # Billions of Chained 2015 Yen
            ("NGDPRSAXDCCAQ", "CA", "CAD"),  # Millions of domestic currency, real
        )
    ),
    *(
        FredAddition(
            f"XTNTVA01{iso2}M667S",
            iso2,
            "external",
            "merchandise_trade_balance",
            "amount_currency",
            "USD",
            "lagging",
            _TRADE_REASON,
            "diff",
        )
        for iso2 in ("DE", "FR", "IT", "JP", "CA", "AU")  # US dollars, exchange rate converted
    ),
)
FRED_ADDITIONS = (
    *FRED_ADDITIONS,
    # South Africa: quarterly (the OECD has no monthly series), seasonally adjusted with vintages.
    FredAddition(
        "LRUNTTTTZAQ156S",
        "ZA",
        "labour",
        "unemployment_rate",
        "rate_percent",
        None,
        "lagging",
        "Employers hire and fire after output has already turned.",
        "diff",
    ),
)
# Portugal's consumer prices were FRED's copy of Eurostat's HICP (CP0000PTM086NEST) from 18 Nov
# 2026; from 19 Nov 2026 they come from Eurostat itself (HICP_GEO below, rule 38).
FRED_ADDITION_BY_ID = {a.id: a for a in FRED_ADDITIONS}


@dataclass(frozen=True)
class OnsSeries:
    id: str  # QuFin id: ONS_<CDID>
    cdid: str
    path: str  # the time series page; /data on it returns JSON
    frequency: Literal["Monthly", "Quarterly"]
    title: str
    units: str
    concept: str
    dimension: Literal["growth", "inflation", "labour", "external"]
    unit_kind: str
    currency: str | None
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    published_as_change: bool = False


ONS_SERIES: tuple[OnsSeries, ...] = (
    OnsSeries(
        "ONS_MGSX",
        "MGSX",
        "employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms",
        "Monthly",
        "Unemployment rate (aged 16 and over, seasonally adjusted)",
        "Percent",
        "unemployment_rate",
        "labour",
        "rate_percent",
        None,
        "lagging",
        "Employers hire and fire after output has already turned.",
        "diff",
    ),
    OnsSeries(
        "ONS_ABMI",
        "ABMI",
        "economy/grossdomesticproductgdp/timeseries/abmi/qna",
        "Quarterly",
        "Gross domestic product: chained volume measures, seasonally adjusted",
        "Millions of Pounds, chained volume measures",
        "real_gdp",
        "growth",
        "amount_currency",
        "GBP",
        "coincident",
        _GDP_REASON,
        "pct",
    ),
    OnsSeries(
        "ONS_DKO8",
        "DKO8",
        "economy/inflationandpriceindices/timeseries/dko8/mm23",
        "Monthly",
        "CPI 12-month rate: excluding energy, food, alcoholic beverages and tobacco",
        "Percentage change",
        "core_consumer_prices",
        "inflation",
        "rate_percent",
        None,
        "lagging",
        "Prices follow activity with a lag.",
        "diff",
        published_as_change=True,
    ),
)
ONS_SERIES = (
    *ONS_SERIES,
    OnsSeries(
        "ONS_BOKI",
        "BOKI",
        "economy/nationalaccounts/balanceofpayments/timeseries/boki/mret",
        "Monthly",
        "Trade in goods: worldwide balance, balance of payments basis, current prices, SA",
        "Millions of Pounds",
        "merchandise_trade_balance",
        "external",
        "amount_currency",
        "GBP",
        "lagging",
        _TRADE_REASON,
        "diff",
    ),
)
ONS_BY_ID = {s.id: s for s in ONS_SERIES}
ONS_COUNTRY = "GB"

# Residential property prices (BIS, nominal index 2010 = 100, quarterly) for the economies the BIS
# covers that QuFin tracks. Russia is left out: the BIS stopped receiving official Russian data
# in 2022 for its other series (see bis_ids.py). Japan is left out too: its latest quarter was
# 2025 Q4 on 13 Nov 2026 while every other economy had 2026 Q2, so the release check failed it as
# overdue (rule 1); add it when the BIS catches up. The euro area has no property price series.
SPP_AREAS: tuple[str, ...] = (
    "AU", "BR", "CA", "CH", "CN", "CZ", "DE", "DK", "FR", "GB", "HK", "HU", "ID", "IN", "IT",
    "KR", "MX", "NO", "NZ", "PL", "SE", "SG", "TR", "US", "ZA",
)  # fmt: skip

# Kuwait publishes a policy rate (the BIS carries it, current to October 2026); Qatar does not.
KUWAIT_POLICY = "KW"
# Germany, France and Italy: effective exchange rates and credit are published per country; their
# policy rate is the ECB's, already stored for the euro area (rule 16).
EURO_MEMBERS: tuple[str, ...] = ("DE", "FR", "IT")


@dataclass(frozen=True)
class EurostatSeries:
    id: str  # QuFin id: ESTAT_<MEASURE>_<geo>
    country: str  # ISO2 ("EA" for the euro area)
    dataset: str
    filters: dict[str, str]
    title: str
    units: str
    adjustment: str
    concept: str
    dimension: Literal["growth", "inflation", "labour", "external"]
    unit_kind: str
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    published_as_change: bool = False
    release: str = "Eurostat"
    frequency: Literal["Monthly", "Quarterly"] = "Monthly"
    currency: str | None = None  # for an amount in a currency


# Industrial production (seasonally and calendar adjusted, 2021 = 100) for the euro area and its
# three largest economies, and core HICP for the three (the euro area's is already stored from
# the ECB, rule 16). FRED's copies stopped in 2024 and 2025 (see above). Checked 13 Nov 2026:
# production to September 2026 and from 1990; core HICP (annual rate, COICOP 2018 dataset
# `prc_hicp_minr`) to October 2026 and from 1997. The old `prc_hicp_midx` ends in December 2025.
_IP = {"freq": "M", "indic_bt": "PRD", "nace_r2": "B-D", "s_adj": "SCA", "unit": "I21"}
_CORE = {"freq": "M", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD"}
EUROSTAT_SERIES: tuple[EurostatSeries, ...] = (
    *(
        EurostatSeries(
            f"ESTAT_IP_{geo}",
            iso2,
            "sts_inpr_m",
            {**_IP, "geo": geo},
            f"Production in industry, seasonally and calendar adjusted, {geo}",
            "Index, 2021=100",
            "Seasonally and Calendar Adjusted",
            "industrial_production",
            "growth",
            "index",
            "coincident",
            "Output is the cycle itself: production moves with it.",
            "pct",
            release="Eurostat Short-term business statistics",
        )
        for geo, iso2 in (("EA21", "EA"), ("DE", "DE"), ("FR", "FR"), ("IT", "IT"))
    ),
    *(
        EurostatSeries(
            f"ESTAT_CORE_{geo}",
            geo,
            "prc_hicp_minr",
            {**_CORE, "geo": geo},
            f"HICP excluding energy, food, alcohol and tobacco: annual rate of change, {geo}",
            "Percentage change",
            "Not Seasonally Adjusted",
            "core_consumer_prices",
            "inflation",
            "rate_percent",
            "lagging",
            "Prices follow activity with a lag.",
            "diff",
            published_as_change=True,
            release="Eurostat HICP",
        )
        for geo in ("DE", "FR", "IT")
    ),
)
# Monthly unemployment (seasonally adjusted, percent of the labour force, ages 15 to 74 and over as
# Eurostat defines it) for the EU members that had only the World Bank's annual figure
# (rule 38 (b)):
# probed live on 13 Nov 2026, current to September or October 2026. Greece is "EL" at Eurostat.
# Bulgaria and Malta answered HTTP 307 on 13 Nov, during Eurostat's announced maintenance window;
# both answered 200 on 14 Nov, so they were loaded then.
_UNE = {"freq": "M", "s_adj": "SA", "age": "TOTAL", "unit": "PC_ACT", "sex": "T"}
_UNE_GEO: dict[str, str] = {
    "AT": "AT",
    "BE": "BE",
    "BG": "BG",
    "HR": "HR",
    "CY": "CY",
    "EE": "EE",
    "FI": "FI",
    "EL": "GR",
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
}
EUROSTAT_SERIES = (
    *EUROSTAT_SERIES,
    *(
        EurostatSeries(
            f"ESTAT_UNE_{geo}",
            iso2,
            "une_rt_m",
            {**_UNE, "geo": geo},
            f"Unemployment rate, seasonally adjusted, total, {geo}",
            "Percent",
            "Seasonally Adjusted",
            "unemployment_rate",
            "labour",
            "rate_percent",
            "lagging",
            "Employers hire and fire after output has already turned.",
            "diff",
            release="Eurostat Labour market",
        )
        for geo, iso2 in _UNE_GEO.items()
    ),
)
# Rule 38, 19 Nov 2026: consumer prices from Eurostat's HICP, all items, annual rate of change
# (`prc_hicp_minr`), for every economy where Eurostat's latest month was ahead of the series then
# serving the pair (October 2026 against September or August; Kosovo had none). For Albania,
# Belgium, Switzerland, Estonia, Luxembourg and Slovenia the IMF series was level with it
# (October too); the tie goes to the more native source, Eurostat (rule 38, Part 0). Eurostat
# publishes the final HICP about 15 to 18 days after the month and flags early figures `e`;
# the licence covers EU, EFTA and candidate economies (Bosnia, Moldova and Ukraine are not
# served). Greece is "EL" at Eurostat. See docs/assumptions-register.md section 4r.
HICP_GEO: dict[str, str] = {
    "AL": "AL", "AT": "AT", "BE": "BE", "BG": "BG", "CH": "CH", "CY": "CY", "CZ": "CZ",
    "DE": "DE", "DK": "DK", "EE": "EE", "ES": "ES", "FI": "FI", "FR": "FR", "GR": "EL",
    "HR": "HR", "HU": "HU", "IE": "IE", "IS": "IS", "IT": "IT", "LT": "LT", "LU": "LU",
    "LV": "LV", "ME": "ME", "MK": "MK", "MT": "MT", "NL": "NL", "NO": "NO", "PL": "PL",
    "PT": "PT", "RO": "RO", "RS": "RS", "SE": "SE", "SI": "SI", "SK": "SK", "TR": "TR",
    "XK": "XK",
}  # fmt: skip
_HICP = {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL"}
EUROSTAT_SERIES = (
    *EUROSTAT_SERIES,
    *(
        EurostatSeries(
            f"ESTAT_HICP_{geo}",
            iso2,
            "prc_hicp_minr",
            {**_HICP, "geo": geo},
            f"HICP, all items: annual rate of change, {geo}",
            "Percentage change",
            "Not Seasonally Adjusted",
            "consumer_prices",
            "inflation",
            "rate_percent",
            "lagging",
            "Inflation follows the cycle; it confirms rather than predicts.",
            "diff",
            published_as_change=True,
            release="Eurostat HICP",
        )
        for iso2, geo in HICP_GEO.items()
    ),
)
# Batch B, 22 Nov 2026: industrial production and core HICP, the same measures as above, for the
# economies Eurostat serves (rule 38, Bloc aggregator first) that had none. Each was staged and
# loaded over its full history with no missing month and the latest month in line with the
# others (production 2026-09, core HICP 2026-10). Belgium's production ended a month earlier and
# stays staged. Greece is "EL" at Eurostat. See docs/assumptions-register.md, section 5e.
BATCH_B_CORE: dict[str, str] = {
    "AL": "AL",
    "AT": "AT",
    "BE": "BE",
    "BG": "BG",
    "CH": "CH",
    "CY": "CY",
    "CZ": "CZ",
    "DK": "DK",
    "EE": "EE",
    "ES": "ES",
    "FI": "FI",
    "EL": "GR",
    "HR": "HR",
    "HU": "HU",
    "IE": "IE",
    "IS": "IS",
    "LT": "LT",
    "LU": "LU",
    "LV": "LV",
    "ME": "ME",
    "MK": "MK",
    "MT": "MT",
    "NL": "NL",
    "NO": "NO",
    "PL": "PL",
    "PT": "PT",
    "RO": "RO",
    "RS": "RS",
    "SE": "SE",
    "SI": "SI",
    "SK": "SK",
    "TR": "TR",
    "XK": "XK",
}
BATCH_B_IP: dict[str, str] = {
    "AT": "AT",
    "BG": "BG",
    "CH": "CH",
    "CY": "CY",
    "CZ": "CZ",
    "DK": "DK",
    "EE": "EE",
    "ES": "ES",
    "FI": "FI",
    "EL": "GR",
    "HR": "HR",
    "HU": "HU",
    "IE": "IE",
    "LT": "LT",
    "LU": "LU",
    "LV": "LV",
    "ME": "ME",
    "MK": "MK",
    "MT": "MT",
    "NL": "NL",
    "NO": "NO",
    "PL": "PL",
    "PT": "PT",
    "RO": "RO",
    "RS": "RS",
    "SE": "SE",
    "SI": "SI",
    "SK": "SK",
    "TR": "TR",
}
EUROSTAT_SERIES = (
    *EUROSTAT_SERIES,
    *(
        EurostatSeries(
            f"ESTAT_IP_{geo}",
            iso2,
            "sts_inpr_m",
            {**_IP, "geo": geo},
            f"Production in industry, seasonally and calendar adjusted, {geo}",
            "Index, 2021=100",
            "Seasonally and Calendar Adjusted",
            "industrial_production",
            "growth",
            "index",
            "coincident",
            "Output is the cycle itself: production moves with it.",
            "pct",
            release="Eurostat Short-term business statistics",
        )
        for geo, iso2 in BATCH_B_IP.items()
    ),
    *(
        EurostatSeries(
            f"ESTAT_CORE_{geo}",
            iso2,
            "prc_hicp_minr",
            {**_CORE, "geo": geo},
            f"HICP excluding energy, food, alcohol and tobacco: annual rate of change, {geo}",
            "Percentage change",
            "Not Seasonally Adjusted",
            "core_consumer_prices",
            "inflation",
            "rate_percent",
            "lagging",
            "Prices follow activity with a lag.",
            "diff",
            published_as_change=True,
            release="Eurostat HICP",
        )
        for geo, iso2 in BATCH_B_CORE.items()
    ),
)
# Batch C, 22 Nov 2026: real GDP (chain linked volumes 2020, national currency, seasonally and
# calendar adjusted, `namq_10_gdp`) and the current account (percent of GDP, `ei_bpm6ca_q`) for
# the economies Eurostat serves that had none (rule 38, Bloc aggregator first). Both are
# quarterly, each quarter dated at its first month. Each was staged and loaded over its full
# history with no missing quarter. See docs/assumptions-register.md, section 5g.
_GDP = {"freq": "Q", "unit": "CLV20_MNAC", "s_adj": "SCA", "na_item": "B1GQ"}
_CA = {
    "freq": "Q",
    "unit": "PC_GDP",
    "s_adj": "NSA",
    "sector10": "S1",
    "sectpart": "S1",
    "partner": "WRL_REST",
    "stk_flow": "BAL",
    "bop_item": "CA",
}
BATCH_C_GDP: dict[str, str] = {  # Eurostat geo -> currency
    "CH": "CHF", "NO": "NOK", "SE": "SEK", "DK": "DKK", "CZ": "CZK", "HU": "HUF", "PL": "PLN",
    "TR": "TRY",
}  # fmt: skip
BATCH_C_CA: tuple[str, ...] = (
    "DE", "FR", "IT", "CH", "NO", "SE", "DK", "CZ", "HU", "PL", "TR",
)  # fmt: skip
# Batch E, 25 Nov 2026: the 24 staged EU-country goods balances. Eurostat uses `EL` for Greece.
BATCH_E_TRADE: dict[str, str] = {
    "AT": "AT", "BE": "BE", "BG": "BG", "HR": "HR", "CY": "CY", "CZ": "CZ", "DK": "DK",
    "EE": "EE", "EL": "GR", "ES": "ES", "FI": "FI", "HU": "HU", "IE": "IE",
    "LT": "LT", "LU": "LU", "LV": "LV", "MT": "MT", "NL": "NL", "PL": "PL", "PT": "PT",
    "RO": "RO", "SE": "SE", "SI": "SI", "SK": "SK",
}  # fmt: skip
EUROSTAT_SERIES = (
    *EUROSTAT_SERIES,
    *(
        EurostatSeries(
            f"ESTAT_GDP_{geo}",
            geo,
            "namq_10_gdp",
            {**_GDP, "geo": geo},
            f"Real GDP, chain linked volumes (2020), seasonally and calendar adjusted, {geo}",
            "National currency, chain linked volumes (2020)",
            "Seasonally and Calendar Adjusted",
            "real_gdp",
            "growth",
            "amount_currency",
            "coincident",
            "Output is the cycle itself: real GDP moves with it.",
            "pct",
            release="Eurostat National accounts",
            frequency="Quarterly",
            currency=currency,
        )
        for geo, currency in BATCH_C_GDP.items()
    ),
    *(
        EurostatSeries(
            f"ESTAT_CA_{geo}",
            geo,
            "ei_bpm6ca_q",
            {**_CA, "geo": geo},
            f"Current account balance with the rest of the world, percent of GDP, {geo}",
            "Percent of GDP",
            "Not Seasonally Adjusted",
            "current_account_to_gdp",
            "external",
            "ratio",
            "lagging",
            "The external balance adjusts after the cycle has turned.",
            "diff",
            release="Eurostat Balance of payments",
            frequency="Quarterly",
        )
        for geo in BATCH_C_CA
    ),
    *(
        EurostatSeries(
            f"ESTAT_TRADE_{geo}",
            country,
            "ei_eteu27_2020_m",
            {
                "freq": "M",
                "stk_flow": "BAL_RT",
                "unit": "MIO-EUR-SA",
                "partner": "WORLD",
                "indic": "ET-T",
                "geo": geo,
            },
            f"Goods trade balance with the world, {geo}",
            "Million euro",
            "Seasonally and Working Day Adjusted",
            "merchandise_trade_balance",
            "external",
            "amount_currency",
            "lagging",
            "Trade balances adjust after the cycle has turned.",
            "diff",
            release="Eurostat International trade in goods",
            frequency="Monthly",
            currency="EUR",
        )
        for geo, country in BATCH_E_TRADE.items()
    ),
)
EUROSTAT_BY_ID = {s.id: s for s in EUROSTAT_SERIES}


@dataclass(frozen=True)
class OecdFlowSeries:
    id: str  # QuFin id: OECD_<MEASURE>_<area>
    country: str  # ISO2
    flow: str
    key: str  # fully specified: the OECD's partial keys return broken histories
    title: str
    units: str
    adjustment: str
    concept: str
    dimension: Literal["growth", "external"]
    unit_kind: str
    currency: str | None
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    release: str
    frequency: Literal["Monthly", "Quarterly"] = "Quarterly"


# Batch C, 22 Nov 2026: the OECD's quarterly national accounts (real GDP, chained volumes,
# national currency, seasonally adjusted) and balance of payments (current account balance,
# percent of GDP) for economies that had none and that Eurostat does not serve. Each was staged
# and loaded over its full history first.
_QNA_FLOW = "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_NATIO_CURR,"
_BOP_FLOW = "OECD.SDD.TPS,DSD_BOP@DF_BOP,"
BATCH_C_OECD_GDP: dict[str, tuple[str, str]] = {  # area -> (ISO2, currency)
    "EA": ("EA", "EUR"), "NZL": ("NZ", "NZD"), "BRA": ("BR", "BRL"), "SAU": ("SA", "SAR"),
    "COL": ("CO", "COP"),
}  # fmt: skip
BATCH_C_OECD_CA: dict[str, str] = {
    "USA": "US", "EA": "EA", "GBR": "GB", "JPN": "JP", "CHN": "CN", "IND": "IN", "BRA": "BR",
    "ZAF": "ZA", "ARG": "AR", "IDN": "ID", "SAU": "SA", "CHL": "CL",
}  # fmt: skip
_OECD_FLOW_READY: tuple[OecdFlowSeries, ...] = (
    *(
        OecdFlowSeries(
            f"OECD_GDP_{area}",
            iso2,
            _QNA_FLOW,
            ".".join(["Q", "Y", area, "S1", "S1", "B1GQ", "", "", "", "XDC", "L", "N", ""]),
            f"Real GDP, chained volumes, national currency, seasonally adjusted, {area}",
            "National currency, chained volumes",
            "Seasonally Adjusted",
            "real_gdp",
            "growth",
            "amount_currency",
            currency,
            "coincident",
            "Output is the cycle itself: real GDP moves with it.",
            "pct",
            "OECD Quarterly national accounts",
        )
        for area, (iso2, currency) in BATCH_C_OECD_GDP.items()
    ),
    *(
        OecdFlowSeries(
            f"OECD_CA_{area}",
            iso2,
            _BOP_FLOW,
            ".".join([area, "WXD", "CA", "B", "T", "Q", "PT_B1GQ", ""]),
            f"Current account balance, percent of GDP, {area}",
            "Percent of GDP",
            "As published by the OECD",
            "current_account_to_gdp",
            "external",
            "ratio",
            None,
            "lagging",
            "The external balance adjusts after the cycle has turned.",
            "diff",
            "OECD Balance of payments",
        )
        for area, iso2 in BATCH_C_OECD_CA.items()
    ),
)
# Served from 22 Nov 2026 (batch D): the OECD's terms of 1 July 2024 allow any use of its data,
# commercial included, with credit, unless the dataset's metadata names third-party owners; the
# two datasets name none (docs/assumptions-register.md, section 5h).
OECD_FLOW_SERIES: tuple[OecdFlowSeries, ...] = _OECD_FLOW_READY
OECD_FLOW_BY_ID = {s.id: s for s in OECD_FLOW_SERIES}


@dataclass(frozen=True)
class BcbSeries:
    id: str  # QuFin id: BCB_<code>
    code: int  # SGS series code
    title: str
    units: str
    adjustment: str
    concept: str
    dimension: Literal["labour", "external"]
    unit_kind: str
    currency: str | None
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    release: str


# Brazil from the central bank's SGS (keyless, verified live 13 Nov 2026: both to September 2026).
# FRED has no Brazilian unemployment (LRHUTTTTBRM156S does not exist) and the OECD has no monthly
# series. 24369 is the PNAD Continua unemployment rate (moving quarter, monthly, from 2012);
# 22707 is the monthly goods trade balance in millions of US dollars. Neither is seasonally
# adjusted.
BCB_SERIES: tuple[BcbSeries, ...] = (
    BcbSeries(
        "BCB_24369", 24369, "Unemployment rate, PNAD Continua", "Percent",
        "Not Seasonally Adjusted", "unemployment_rate", "labour", "rate_percent", None,
        "lagging", "Employers hire and fire after output has already turned.", "diff",
        "IBGE PNAD Continua (via BCB SGS)",
    ),
    BcbSeries(
        "BCB_22707", 22707, "Trade balance, goods, monthly", "Millions of U.S. Dollars",
        "Not Seasonally Adjusted", "merchandise_trade_balance", "external", "amount_currency",
        "USD",
        "lagging", _TRADE_REASON, "diff", "Balance of payments (via BCB SGS)",
    ),
)  # fmt: skip
BCB_BY_ID = {s.id: s for s in BCB_SERIES}
BCB_COUNTRY = "BR"


@dataclass(frozen=True)
class SingStatSeries:
    id: str
    table: str
    series_no: str
    title: str
    units: str
    concept: str
    release: str


# Singapore from the Department of Statistics Table Builder (keyless, verified live 13 Nov 2026):
# table M182342, row 1 "Total Unemployment Rate, (SA)", quarterly 1992 1Q to 2026 3Q. FRED has none
# and the OECD has no monthly series for Singapore.
SINGSTAT_SERIES: tuple[SingStatSeries, ...] = (
    SingStatSeries(
        "SINGSTAT_UNE",
        "M182342",
        "1",
        "Total unemployment rate, seasonally adjusted",
        "Percent",
        "unemployment_rate",
        "SingStat Labour Force Survey",
    ),
)
SINGSTAT_BY_ID = {s.id: s for s in SINGSTAT_SERIES}
SINGSTAT_COUNTRY = "SG"

# Policy rates added on 13 Nov 2026 (BIS WS_CBPOL, current to October 2026): Chile and Colombia.
NEW_POLICY_AREAS: tuple[str, ...] = ("CL", "CO")
