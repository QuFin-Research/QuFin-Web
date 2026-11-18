"""BIS series (P1-22): which measures, for which economies, from which dataflow.

Checked live on 12 Nov 2026 against the BIS Data Portal API (v2). Every economy below had a
current observation for its measure (latest month September or October 2026, latest quarter
2026 Q1). Left out, and why:

- the United States, except for property prices: FRED carries the US dollar indexes and credit
  series with vintages (rule 17), and the Fed's own policy rate is stored from FRED, but
  FRED's copy of the BIS property price index (not seasonally adjusted, with vintages) was a
  quarter behind the BIS API on 13 Nov 2026 (FRED to 2026 Q1, BIS to Q2), so the BIS is read;
- the euro area for policy rates: the ECB deposit facility rate is already stored (rule 16), so
  Germany, France and Italy (the BIS has no policy rate for them) get effective exchange rates and
  credit only;
- Russia: the BIS stopped receiving Russian official data after 28 Feb 2022 and the coverage
  list marks Russia as undecided (docs/coverage-universe.md);
- Singapore and the United Arab Emirates for policy rates (BIS has none) and the UAE for credit
  (not published).

FRED republishes some of these BIS series, but its copies were two months behind the BIS API on
12 Nov 2026 (UK real effective exchange rate: FRED to July, BIS to September), so the BIS API is
read directly. Kept apart from the catalog so the cycle classification and tests can use it too.

Added 17 Nov 2026 (thirteen further measures; each key and area list was checked live over the
full history, see docs/bis-probe-2026-11-17.md): household and government credit, debt service
ratios, US-dollar credit (global liquidity), central bank total assets, international debt
securities, debt securities issued by government, non-financial and financial corporations,
commercial property prices, and consumer prices for the economies no other source covers. Left
out, and why:

- the United States, again: credit, central bank total assets (WALCL), debt securities and
  debt service are read from FRED where it has them (rule 17), and the BIS global liquidity
  series measure credit to borrowers outside the US. The BIS has a US commercial property index
  (1990 to 2026 Q2); whether FRED carries one could not be checked on 17 Nov 2026 (the FRED key in
  the environment was rejected), so it stays out until it is (docs/assumptions-register.md);
- Russia, as before, and Thailand, Peru, the Philippines and Morocco, which are not in the
  taxonomy;
- any economy whose series is stale (latest period before the usual release) or has missing
  periods in the BIS response: a gap is not filled (rule 3), the economy is left out until the BIS
  fills it;
- Kuwait consumer prices: the BIS series ends in June 2026 while New Zealand's, Malta's and
  Serbia's run to August or September, so the release check marked it overdue on 17 Nov;
- Central bank total assets are the quarterly series: the BIS releases months only in
  quarterly batches (March, June, September, December), which the release check, built for a
  monthly series released monthly, calls overdue between batches (33 of 48 on 17 Nov). Israel,
  Indonesia and South Korea end a quarter earlier than the rest and Kuwait has missing
  quarters, so those four are left out;
- Chile and Colombia consumer prices: the IMF has them (442 and 441 months loaded on 17 Nov
  2026), and the IMF comes before the BIS (rule 16);
- credit to the non-financial sector in total and to non-financial corporations: the first is
  the private sector (stored as the credit-to-GDP ratio) plus the government, the second the
  private sector minus households, so both are derived and not stored (rule 16);
- Japan's commercial property index (it ends two quarters before the others), Greece's (half-yearly)
  and Poland's and Portugal's (annual): `Frequency` here is monthly or quarterly only.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.data.gap_ids import EURO_MEMBERS, KUWAIT_POLICY, NEW_POLICY_AREAS, SPP_AREAS

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
_POLICY_WITH_KUWAIT = (*_POLICY_AREAS, KUWAIT_POLICY, *NEW_POLICY_AREAS)
_EER_AREAS = (*_POLICY_AREAS, "XM", "SG", "AE", *EURO_MEMBERS)
_CREDIT_AREAS = (*_POLICY_AREAS, "XM", "SG", *EURO_MEMBERS)

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
    dimension: Literal["policy", "external", "housing", "fiscal", "inflation"]
    cycle: Literal["leading", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    seasonal_adjustment: str = "Not Seasonally Adjusted"
    # The series dimension that names the economy (the credit flow calls it differently).
    area_dimension: str = "REF_AREA"
    # The dataflow's version: most are 1.0, total credit (WS_TC) is 2.0.
    version: str = "1.0"
    # The BIS UNIT_MULT attribute (Units, Millions, Billions), when it publishes one.
    unit_mult: str | None = None
    # The BIS publishes it as a change or growth rate already: never taken a change of again.
    published_as_change: bool = False
    # How a period's release date is derived: "monthly" and "quarterly" by default (bis_calendar).
    release: Literal["monthly", "quarterly", "cbta", "cpi"] | None = None
    # One request per economy, each with its own series shape: `parts` holds what follows the
    # area in the key (commercial property types and areas differ by country).
    parts: tuple[tuple[str, str], ...] = ()


_TCHH_AREAS = (
    "AR",
    "AT",
    "AU",
    "BE",
    "BR",
    "CA",
    "CH",
    "CL",
    "CN",
    "CO",
    "CZ",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HK",
    "HU",
    "ID",
    "IE",
    "IL",
    "IN",
    "IT",
    "JP",
    "KR",
    "LU",
    "MX",
    "MY",
    "NL",
    "NO",
    "NZ",
    "PL",
    "PT",
    "SA",
    "SE",
    "SG",
    "TR",
    "XM",
    "ZA",
)

_TCGOV_AREAS = (
    "AT",
    "AU",
    "BE",
    "CA",
    "CH",
    "CL",
    "CZ",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HU",
    "IE",
    "IL",
    "IT",
    "JP",
    "KR",
    "LU",
    "NL",
    "NO",
    "PL",
    "PT",
    "SE",
    "TR",
    "XM",
)

_DSRP_AREAS = (
    "AU",
    "BE",
    "BR",
    "CA",
    "CH",
    "CN",
    "CZ",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "HK",
    "HU",
    "ID",
    "IN",
    "IT",
    "JP",
    "KR",
    "MX",
    "MY",
    "NL",
    "NO",
    "PL",
    "PT",
    "SE",
    "TR",
    "ZA",
)

_DSRH_AREAS = (
    "AU",
    "BE",
    "CA",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "IT",
    "JP",
    "KR",
    "NL",
    "NO",
    "PT",
    "SE",
)

_DSRN_AREAS = (
    "AU",
    "BE",
    "CA",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "IT",
    "JP",
    "KR",
    "NL",
    "NO",
    "PT",
    "SE",
)

_GLI_AREAS = (
    "AR",
    "BR",
    "CL",
    "CN",
    "ID",
    "IN",
    "MX",
    "MY",
    "SA",
    "TR",
    "ZA",
)

_CBTA_AREAS = (
    "AE",
    "AR",
    "AT",
    "AU",
    "BE",
    "BR",
    "CA",
    "CH",
    "CL",
    "CN",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HK",
    "HR",
    "HU",
    "IE",
    "IN",
    "IT",
    "JP",
    "LT",
    "LU",
    "LV",
    "MK",
    "MX",
    "MY",
    "NL",
    "NO",
    "NZ",
    "PL",
    "PT",
    "SA",
    "SE",
    "SG",
    "SI",
    "SK",
    "TR",
    "XM",
    "ZA",
)

_IDS_AREAS = (
    "AE",
    "AL",
    "AM",
    "AR",
    "AT",
    "AU",
    "AZ",
    "BA",
    "BE",
    "BG",
    "BH",
    "BR",
    "BY",
    "CA",
    "CH",
    "CL",
    "CM",
    "CN",
    "CO",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EG",
    "ES",
    "FI",
    "FR",
    "GB",
    "GH",
    "GR",
    "HK",
    "HR",
    "HU",
    "ID",
    "IE",
    "IL",
    "IN",
    "IS",
    "IT",
    "JP",
    "KR",
    "LT",
    "LU",
    "LV",
    "ME",
    "MK",
    "MT",
    "MX",
    "MY",
    "NL",
    "NO",
    "NZ",
    "PL",
    "PT",
    "QA",
    "RO",
    "RS",
    "SA",
    "SE",
    "SG",
    "SI",
    "SK",
    "TR",
    "UA",
    "UZ",
    "VE",
    "ZA",
)

_DSSGOV_AREAS = (
    "AR",
    "AT",
    "BE",
    "BG",
    "BR",
    "CA",
    "CH",
    "CN",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HK",
    "HR",
    "HU",
    "ID",
    "IE",
    "IT",
    "JP",
    "KR",
    "LT",
    "LU",
    "LV",
    "MT",
    "MX",
    "MY",
    "NL",
    "PL",
    "PT",
    "RO",
    "SA",
    "SG",
    "SI",
    "SK",
    "TR",
    "ZA",
)

_DSSNFC_AREAS = (
    "AR",
    "AT",
    "BE",
    "BG",
    "BR",
    "CA",
    "CH",
    "CN",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "ID",
    "IE",
    "IT",
    "JP",
    "KR",
    "LU",
    "MT",
    "MX",
    "MY",
    "NL",
    "PL",
    "PT",
    "RO",
    "SG",
    "SI",
    "SK",
    "TR",
    "ZA",
)

_DSSFIN_AREAS = (
    "AR",
    "AT",
    "BE",
    "BG",
    "BR",
    "CA",
    "CH",
    "CN",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "ID",
    "IE",
    "IT",
    "JP",
    "KR",
    "LT",
    "LU",
    "LV",
    "MT",
    "MX",
    "MY",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SG",
    "SI",
    "SK",
    "TR",
    "ZA",
)

# Malta and Serbia moved to Eurostat's HICP on 19 Nov 2026 (rule P, gap_ids.py).
_CPI_AREAS = ("NZ",)

# Commercial property: one series per economy, whole country where the BIS has it, the most general
# property type it has (all commercial, else office and retail, office, retail), all vintages.
# Dimensions after the area: covered area, type, vintage, compiler (any), priced unit (pure price
# index), adjustment (not seasonally adjusted).
_CPP_PARTS = (
    ("DE", "0.A.0.*.6.0"),
    ("ES", "0.A.0.*.6.0"),
    ("ID", "4.A.0.*.6.0"),  # big cities: the BIS has no whole-country series
    ("NL", "0.B.0.*.6.0"),  # offices
    ("SA", "0.C.0.*.6.0"),  # retail
    ("SI", "0.D.0.*.6.0"),  # offices and retail
    ("TR", "0.D.0.*.6.0"),
)
_CPP_AREAS = tuple(area for area, _ in _CPP_PARTS)

_MARKET_DEBT = "Debt outstanding builds over years, so it confirms the cycle after it has turned."


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
            _POLICY_WITH_KUWAIT,
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
        BisMeasure(
            "SPP",
            "WS_SPP",
            "Q.{areas}.N.628",
            "Quarterly",
            "Residential property prices, nominal index",
            "Index, 2010=100",
            None,
            SPP_AREAS,
            "housing",
            "leading",
            "Housing is the most rate-sensitive part of spending, so it turns before the economy.",
            "pct",
        ),
        BisMeasure(
            "TCHH",
            "WS_TC",
            "Q.{areas}.H.A.M.770.A",
            "Quarterly",
            "Credit to households and non-profit institutions, market value, ratio to GDP",
            "Percent of GDP",
            "Per cent",
            _TCHH_AREAS,
            "policy",
            "lagging",
            "Household borrowing builds over years and confirms the cycle after it has turned.",
            "diff",
            area_dimension="BORROWERS_CTY",
            version="2.0",
            unit_mult="Units",
        ),
        BisMeasure(
            "TCGOV",
            "WS_TC",
            "Q.{areas}.G.A.M.770.A",
            "Quarterly",
            "Credit to general government from all sectors, market value, ratio to GDP",
            "Percent of GDP",
            "Per cent",
            _TCGOV_AREAS,
            "fiscal",
            "lagging",
            "Government debt rises in a downturn and falls slowly after, so it follows the cycle.",
            "diff",
            area_dimension="BORROWERS_CTY",
            version="2.0",
            unit_mult="Units",
        ),
        BisMeasure(
            "DSRP",
            "WS_DSR",
            "Q.{areas}.P",
            "Quarterly",
            "Debt service ratio, private non-financial sector",
            "Percent of income",
            None,
            _DSRP_AREAS,
            "policy",
            "leading",
            "BIS research finds a rising debt service burden signals stress before the downturn.",
            "diff",
            area_dimension="BORROWERS_CTY",
        ),
        BisMeasure(
            "DSRH",
            "WS_DSR",
            "Q.{areas}.H",
            "Quarterly",
            "Debt service ratio, households and non-profit institutions",
            "Percent of income",
            None,
            _DSRH_AREAS,
            "policy",
            "leading",
            "BIS research finds a rising debt service burden signals stress before the downturn.",
            "diff",
            area_dimension="BORROWERS_CTY",
        ),
        BisMeasure(
            "DSRN",
            "WS_DSR",
            "Q.{areas}.N",
            "Quarterly",
            "Debt service ratio, non-financial corporations",
            "Percent of income",
            None,
            _DSRN_AREAS,
            "policy",
            "leading",
            "BIS research finds a rising debt service burden signals stress before the downturn.",
            "diff",
            area_dimension="BORROWERS_CTY",
        ),
        BisMeasure(
            "GLIUSD",
            "WS_GLI",
            "Q.USD.{areas}.N.A.I.B.USD",
            "Quarterly",
            "US dollar credit (bank loans and debt securities) to non-bank borrowers",
            "Millions of US dollars",
            None,
            _GLI_AREAS,
            "external",
            "leading",
            "Dollar funding is priced on expectations and tightens before activity does.",
            "pct",
            area_dimension="BORROWERS_CTY",
            unit_mult="Millions",
        ),
        BisMeasure(
            "CBTA",
            "WS_CBTA",
            "Q.{areas}.B.XDC.*.B",
            "Quarterly",
            "Central bank total assets, domestic currency",
            "Billions of Domestic Currency",
            None,
            _CBTA_AREAS,
            "policy",
            "lagging",
            "The central bank changes its balance sheet in response to conditions.",
            "pct",
            unit_mult="Billions",
            release="cbta",
        ),
        BisMeasure(
            "IDS",
            "WS_DEBT_SEC2_PUB",
            "Q.{areas}.3P.1.1.C.A.A.TO1.A.A.A.A.A.I",
            "Quarterly",
            "International debt securities outstanding, all issuers and currencies, by residence",
            "Millions of US dollars",
            None,
            _IDS_AREAS,
            "external",
            "lagging",
            _MARKET_DEBT,
            "pct",
            area_dimension="ISSUER_RES",
        ),
        BisMeasure(
            "DSSGOV",
            "WS_NA_SEC_DSS",
            "Q.N.{areas}.XW.S13.S1.N.L.LE.F3.T._Z.USD._T.N.V.N._T",
            "Quarterly",
            "Debt securities issued by general government, outstanding, nominal value",
            "Billions of US dollars",
            None,
            _DSSGOV_AREAS,
            "fiscal",
            "lagging",
            _MARKET_DEBT,
            "pct",
            unit_mult="Billions",
        ),
        BisMeasure(
            "DSSNFC",
            "WS_NA_SEC_DSS",
            "Q.N.{areas}.XW.S11.S1.N.L.LE.F3.T._Z.USD._T.N.V.N._T",
            "Quarterly",
            "Debt securities issued by non-financial corporations, outstanding, nominal value",
            "Billions of US dollars",
            None,
            _DSSNFC_AREAS,
            "policy",
            "lagging",
            _MARKET_DEBT,
            "pct",
            unit_mult="Billions",
        ),
        BisMeasure(
            "DSSFIN",
            "WS_NA_SEC_DSS",
            "Q.N.{areas}.XW.S12.S1.N.L.LE.F3.T._Z.USD._T.N.V.N._T",
            "Quarterly",
            "Debt securities issued by financial corporations, outstanding, nominal value",
            "Billions of US dollars",
            None,
            _DSSFIN_AREAS,
            "policy",
            "lagging",
            _MARKET_DEBT,
            "pct",
            unit_mult="Billions",
        ),
        BisMeasure(
            "CPP",
            "WS_CPP",
            "Q.{areas}.{part}",
            "Quarterly",
            "Commercial property price index",
            "Index",
            None,
            _CPP_AREAS,
            "housing",
            "leading",
            "Commercial property is priced on expected rents, so it turns before activity.",
            "pct",
            parts=_CPP_PARTS,
        ),
        BisMeasure(
            "CPI",
            "WS_LONG_CPI",
            "M.{areas}.771",
            "Monthly",
            "Consumer prices, year-on-year change",
            "Percent",
            None,
            _CPI_AREAS,
            "inflation",
            "lagging",
            "Prices follow output and wages with a lag.",
            "diff",
            published_as_change=True,
            release="cpi",
        ),
    )
}


# Months the BIS publishes no value for, inclusive: Japan had no policy rate while the Bank of
# Japan ran quantitative easing (the BIS states 4 Apr 2013 to 20 Sep 2016 in its series notes and
# publishes nothing for March 2001 to March 2006 either; it also has no value for March 1999 to
# July 2000, the years of the zero-rate policy, found when loading from 1990 on 13 Nov 2026).
# Any other missing period is a partial response and fails the load.
KNOWN_GAPS: dict[str, tuple[tuple[date, date], ...]] = {
    "BIS_CBPOL_JP": (
        (date(1999, 3, 1), date(2000, 7, 1)),
        (date(2001, 4, 1), date(2006, 2, 1)),
        (date(2013, 5, 1), date(2016, 8, 1)),
    ),
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

# Measures added on 17 Nov 2026: their series load from 1990, or from the BIS's own first period.
NEW_CODES: frozenset[str] = frozenset(
    {
        "TCHH", "TCGOV", "DSRP", "DSRH", "DSRN", "GLIUSD", "CBTA", "IDS", "DSSGOV", "DSSNFC",
        "DSSFIN", "CPP", "CPI",
    }
)  # fmt: skip
