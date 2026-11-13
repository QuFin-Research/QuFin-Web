"""Series added to close coverage gaps (Sprints 1-4 of the v3 workbook), each checked at its source.

Checked live on 13 Nov 2026. What was added, and what was left out and why:

- FRED/ALFRED (Rule H): real GDP for Germany, France, Italy, Japan and Canada, and the goods trade
  balance of five economies (the UK is left out: its series fell overdue on 13 Nov 2026, because
  FRED posts the OECD's UK figures every second month), all seasonally adjusted with vintages.
  Left out because FRED's copy is frozen: industrial production (`*PROINDMISMEI`, last March
  2024) and core CPI (`*CPICORMINMEI`,
  last March 2025 or June 2021), the OECD's MEI series that FRED no longer updates; the UK real GDP
  series `CLVMNACSCAB1GQUK` (marked DISCONTINUED, last July 2020); and the Brazilian and South
  African unemployment series (`LRHUTTTT{BR,ZA}M156S` do not exist on FRED).
- ONS (Rule H, UK fallback): unemployment rate, real GDP and core CPI, where FRED has no current
  seasonally adjusted series with vintages. The ONS publishes the latest values only, so each period
  is dated by its usual release lag, erring late (rule 9).
- Every series here starts in 1990 where the source goes back that far (Rule I).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

HISTORY_START = date(1990, 1, 1)  # Rule I: the training horizon for every series added from now on


@dataclass(frozen=True)
class FredAddition:
    id: str
    country: str  # ISO2
    dimension: Literal["growth", "external"]
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
    dimension: Literal["growth", "inflation"]
    unit_kind: str
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    published_as_change: bool = False
    release: str = "Eurostat"


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
EUROSTAT_BY_ID = {s.id: s for s in EUROSTAT_SERIES}
