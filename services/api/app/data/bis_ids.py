"""BIS series (P1-22): which measures, for which economies, from which dataflow.

Checked live on 12 Nov 2026 against the BIS Data Portal API (v2). Every economy below had a
current observation for its measure (latest month September or October 2026, latest quarter
2026 Q1). Left out, and why:

- the United States: FRED carries the US dollar indexes and credit series with vintages
  (rule 17), and the Fed's own policy rate is stored from FRED;
- the euro area for policy rates: the ECB deposit facility rate is already stored (rule 16);
- Russia: the BIS stopped receiving Russian official data after 28 Feb 2022 and the coverage
  list marks Russia as undecided (docs/coverage-universe.md);
- Singapore and the United Arab Emirates for policy rates (BIS has none) and the UAE for credit
  (not published).

FRED republishes some of these BIS series, but its copies were two months behind the BIS API on
12 Nov 2026 (UK real effective exchange rate: FRED to July, BIS to September), so the BIS API is
read directly. Kept apart from the catalog so the cycle classification and tests can use it too.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Frequency = Literal["Monthly", "Quarterly"]

# BIS area code -> QuFin country code. XM is the BIS code for the euro area.
BIS_COUNTRY: dict[str, str] = {"XM": "EA"}

_POLICY_AREAS = (
    "GB",
    "JP",
    "CA",
    "AU",
    "NZ",
    "CH",
    "NO",
    "SE",
    "DK",
    "CZ",
    "HU",
    "PL",
    "CN",
    "IN",
    "MX",
    "BR",
    "TR",
    "ZA",
    "HK",
    "KR",
    "SA",
)
_EER_AREAS = (*_POLICY_AREAS, "XM", "SG", "AE")
_CREDIT_AREAS = (*_POLICY_AREAS, "XM", "SG")

_MARKET = "Market prices discount the future, so they turn before activity."


@dataclass(frozen=True)
class BisMeasure:
    code: str  # in the QuFin id: BIS_<code>_<area>
    flow: str  # BIS dataflow id
    key: str  # series key with {areas} for the economies (joined with "+")
    frequency: Frequency
    title: str
    units: str
    # The BIS UNIT_MEASURE attribute the units were verified against, when it publishes one.
    unit_measure: str | None
    areas: tuple[str, ...]
    dimension: Literal["policy", "external"]
    cycle: Literal["leading", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    seasonal_adjustment: str = "Not Seasonally Adjusted"
    # The series dimension that names the economy (the credit flow calls it differently).
    area_dimension: str = "REF_AREA"


MEASURES: dict[str, BisMeasure] = {
    m.code: m
    for m in (
        BisMeasure(
            "CBPOL",
            "WS_CBPOL",
            "M.{areas}",
            "Monthly",
            "Central bank policy rate (end of month)",
            "Percent per annum",
            None,
            _POLICY_AREAS,
            "policy",
            "lagging",
            "Central banks move rates after the data have turned.",
            "diff",
        ),
        BisMeasure(
            "NEER",
            "WS_EER",
            "M.N.B.{areas}",
            "Monthly",
            "Nominal effective exchange rate, broad basket (64 economies)",
            "Index, 2020=100",
            "Index, 2020 = 100",
            _EER_AREAS,
            "external",
            "leading",
            _MARKET,
            "pct",
        ),
        BisMeasure(
            "REER",
            "WS_EER",
            "M.R.B.{areas}",
            "Monthly",
            "Real effective exchange rate, broad basket (64 economies)",
            "Index, 2020=100",
            "Index, 2020 = 100",
            _EER_AREAS,
            "external",
            "leading",
            _MARKET,
            "pct",
        ),
        BisMeasure(
            "CREDIT",
            "WS_CREDIT_GAP",
            "Q.{areas}.P.A.A",
            "Quarterly",
            "Credit to the private non-financial sector, ratio to GDP",
            "Percent of GDP",
            None,
            _CREDIT_AREAS,
            "policy",
            "lagging",
            "Credit builds over years and confirms the cycle after it has turned.",
            "diff",
            area_dimension="BORROWERS_CTY",
        ),
        BisMeasure(
            "CREDGAP",
            "WS_CREDIT_GAP",
            "Q.{areas}.P.A.C",
            "Quarterly",
            "Credit-to-GDP gap (actual minus HP-filter trend)",
            "Percent of GDP",
            None,
            _CREDIT_AREAS,
            "policy",
            "leading",
            "A credit boom above trend signals financial stress ahead of the downturn it causes.",
            "diff",
            area_dimension="BORROWERS_CTY",
        ),
    )
}


# Months the BIS publishes no value for, inclusive: Japan had no policy rate while the Bank of
# Japan ran quantitative easing (the BIS states 4 Apr 2013 to 20 Sep 2016 in its series notes and
# publishes nothing for March 2001 to March 2006 either). Any other missing period is a partial
# response and fails the load.
KNOWN_GAPS: dict[str, tuple[tuple[date, date], ...]] = {
    "BIS_CBPOL_JP": ((date(2001, 4, 1), date(2006, 2, 1)), (date(2013, 5, 1), date(2016, 8, 1))),
}


def country_of(area: str) -> str:
    return BIS_COUNTRY.get(area, area)


# QuFin id -> (measure code, BIS area).
BIS_SERIES: dict[str, tuple[str, str]] = {
    f"BIS_{m.code}_{area}": (m.code, area) for m in MEASURES.values() for area in m.areas
}

# Every BIS series -> country.
BIS_COUNTRIES: dict[str, str] = {
    series_id: country_of(area) for series_id, (_code, area) in BIS_SERIES.items()
}
