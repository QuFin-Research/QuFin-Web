"""Canonical taxonomy: eight macro pillars, countries and series codes (ADR 0007).

Every stored series gets a canonical code, `<ISO3>.<PILLAR>.<INDICATOR>.<FREQ>.<ADJUSTMENT>`
(for example `USA.MONETARY.POLICY_RATE.M.NSA`), next to its source id (the native ticker, which
stays the key the connectors, tests and API paths use). The code is derived, never typed:
the country from `COUNTRIES`, the pillar from the catalog, the indicator from the concept
(`app/data/indicator_concepts.py`, rule 18), frequency and adjustment from what the source states.
Two series with the same code would be duplicates (rule 16), so the code is unique in the database.

Pillars are the eight macro pillars of the scorecard plus two reference classes that are stored
and shown but never scored: ENERGY (oil supply and demand) and MARKETS (reference prices).
"""

import re
from dataclasses import dataclass
from typing import Literal

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID
from app.domain.freshness import frequency_code

Pillar = Literal[
    "GROWTH",
    "INFLATION",
    "LABOR",
    "MONETARY",
    "SURVEYS",
    "CONSUMPTION",
    "TRADE",
    "FISCAL",
    "ENERGY",
    "MARKETS",
]
PILLARS: tuple[str, ...] = (
    "GROWTH",
    "INFLATION",
    "LABOR",
    "MONETARY",
    "SURVEYS",
    "CONSUMPTION",
    "TRADE",
    "FISCAL",
)
REFERENCE_CLASSES: tuple[str, ...] = ("ENERGY", "MARKETS")

# The catalog's `dimension` (what the live scorecard uses today) onto the eight pillars.
DIMENSION_PILLAR: dict[str, str] = {
    "growth": "GROWTH",
    "inflation": "INFLATION",
    "labour": "LABOR",
    "policy": "MONETARY",
    "sentiment": "SURVEYS",
    "external": "TRADE",
    "fiscal": "FISCAL",
    "energy": "ENERGY",
    "markets": "MARKETS",
}

# Where today's coarse dimension puts an indicator in the wrong pillar. Surveys were filed under
# growth, consumption under growth and policy, financial conditions and the dollar under
# sentiment, and the employment cost index under external.
CONCEPT_PILLAR: dict[str, str] = {
    "business_confidence": "SURVEYS",
    "consumer_sentiment": "SURVEYS",
    "dallas_fed_manufacturing": "SURVEYS",
    "empire_state_manufacturing": "SURVEYS",
    "manufacturing_new_orders_survey": "SURVEYS",
    "real_consumer_spending": "CONSUMPTION",
    "real_retail_sales": "CONSUMPTION",
    "personal_income": "CONSUMPTION",
    "real_income_excl_transfers": "CONSUMPTION",
    "consumer_credit": "CONSUMPTION",
    "corporate_credit_spread": "MONETARY",
    "financial_conditions": "MONETARY",
    "financial_stress": "MONETARY",
    "trade_weighted_currency": "TRADE",
    "employment_cost_index": "LABOR",
}

# What the live scorecard scores today (five pillars, `app/domain/scorecard.py`), as pillars.
SCORED_DIMENSION_PILLAR: dict[str, str] = {
    "growth": "GROWTH",
    "inflation": "INFLATION",
    "labour": "LABOR",
    "policy": "MONETARY",
    "sentiment": "SURVEYS",
}


@dataclass(frozen=True)
class Country:
    iso3: str
    iso2: str
    name: str
    currency: str
    central_bank: str
    g7: bool = False
    g20: bool = False
    gcc: bool = False
    em: bool = False  # emerging market: not an IMF advanced economy (WEO April 2026, Table B)


_ECB = "European Central Bank"
COUNTRIES: tuple[Country, ...] = (
    Country(
        "USA",
        "US",
        "United States",
        "USD",
        "Board of Governors of the Federal Reserve System",
        g7=True,
        g20=True,
    ),
    # The euro area is not a country: ISO has no code for it, so "EMU" (the IMF and OECD use the
    # same idea). The EU is the G20 member.
    Country("EMU", "EA", "Euro Area", "EUR", _ECB, g20=True),
    Country("GBR", "GB", "United Kingdom", "GBP", "Bank of England", g7=True, g20=True),
    Country("JPN", "JP", "Japan", "JPY", "Bank of Japan", g7=True, g20=True),
    Country("CAN", "CA", "Canada", "CAD", "Bank of Canada", g7=True, g20=True),
    Country("DEU", "DE", "Germany", "EUR", "Deutsche Bundesbank", g7=True, g20=True),
    Country("FRA", "FR", "France", "EUR", "Bank of France", g7=True, g20=True),
    Country("ITA", "IT", "Italy", "EUR", "Bank of Italy", g7=True, g20=True),
    Country("AUS", "AU", "Australia", "AUD", "Reserve Bank of Australia", g20=True),
    Country("NZL", "NZ", "New Zealand", "NZD", "Reserve Bank of New Zealand"),
    Country("CHE", "CH", "Switzerland", "CHF", "Swiss National Bank"),
    Country("NOR", "NO", "Norway", "NOK", "Central Bank of Norway"),
    Country("SWE", "SE", "Sweden", "SEK", "Sveriges Riksbank"),
    Country("DNK", "DK", "Denmark", "DKK", "Danmarks Nationalbank"),
    Country("CZE", "CZ", "Czech Republic", "CZK", "Czech National Bank"),
    Country("HUN", "HU", "Hungary", "HUF", "Central Bank of Hungary", em=True),
    Country("POL", "PL", "Poland", "PLN", "Narodowy Bank Polski", g20=True, em=True),
    Country("CHN", "CN", "China", "CNY", "People's Bank of China", g20=True, em=True),
    Country("IND", "IN", "India", "INR", "Reserve Bank of India", g20=True, em=True),
    Country("MEX", "MX", "Mexico", "MXN", "Bank of Mexico", g20=True, em=True),
    Country("BRA", "BR", "Brazil", "BRL", "Central Bank of Brazil", g20=True, em=True),
    Country(
        "TUR", "TR", "Turkey", "TRY", "Central Bank of the Republic of Türkiye", g20=True, em=True
    ),
    Country("ZAF", "ZA", "South Africa", "ZAR", "South African Reserve Bank", em=True),
    Country("KOR", "KR", "South Korea", "KRW", "Bank of Korea", g20=True),
    Country("HKG", "HK", "Hong Kong", "HKD", "Hong Kong Monetary Authority"),
    Country("SGP", "SG", "Singapore", "SGD", "Monetary Authority of Singapore"),
    Country("ARG", "AR", "Argentina", "ARS", "Central Bank of Argentina", g20=True, em=True),
    Country("IDN", "ID", "Indonesia", "IDR", "Bank Indonesia", g20=True, em=True),
    Country(
        "RUS", "RU", "Russia", "RUB", "Central Bank of the Russian Federation", g20=True, em=True
    ),
    Country("SAU", "SA", "Saudi Arabia", "SAR", "Saudi Central Bank", g20=True, gcc=True, em=True),
    Country(
        "ARE",
        "AE",
        "United Arab Emirates",
        "AED",
        "Central Bank of the United Arab Emirates",
        gcc=True,
        em=True,
    ),
    Country("KWT", "KW", "Kuwait", "KWD", "Central Bank of Kuwait", gcc=True, em=True),
    Country("QAT", "QA", "Qatar", "QAR", "Qatar Central Bank", gcc=True, em=True),
    Country("BHR", "BH", "Bahrain", "BHD", "Central Bank of Bahrain", gcc=True, em=True),
    Country("OMN", "OM", "Oman", "OMR", "Central Bank of Oman", gcc=True, em=True),
)
COUNTRY_BY_ISO2 = {c.iso2: c for c in COUNTRIES}
COUNTRY_BY_ISO3 = {c.iso3: c for c in COUNTRIES}

# Seasonal adjustment as the source states it, in the short codes used in series codes.
# SA/NSA/SAAR are the usual three; AA (the OECD's amplitude adjustment of its composite indicators)
# and SWDA (seasonal and working-day) differ from plain SA, so they keep their own codes.
ADJUSTMENTS: dict[str, str] = {
    "not seasonally adjusted": "NSA",
    "seasonally adjusted": "SA",
    "seasonally adjusted annual rate": "SAAR",
    "seasonally and working day adjusted": "SWDA",
    "amplitude adjusted (oecd)": "AA",
    # The EIA states the short codes themselves.
    "nsa": "NSA",
    "sa": "SA",
    "saar": "SAAR",
}

_SCALE = re.compile(r"^(level in )?(thousands?|millions?|billions?|trillions?)\b")
_SCALE_VALUE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}


class TaxonomyError(ValueError):
    pass


def adjustment_code(seasonal_adjustment: str) -> str:
    code = ADJUSTMENTS.get(seasonal_adjustment.strip().lower())
    if code is None:
        raise TaxonomyError(f"Unknown seasonal adjustment {seasonal_adjustment!r}: add it")
    return code


def scale_of(units: str) -> float:
    """The multiplier of the unit text ("Millions of Dollars" -> 1e6), 1 when it has none.

    Anchored at the start, so "Dollars per Million BTU" is not read as millions.
    """
    match = _SCALE.match(units.strip().lower())
    if not match:
        return 1.0
    return _SCALE_VALUE[match.group(2).rstrip("s")]


def pillar_for(country: str, series_id: str) -> str | None:
    """The pillar of a catalog series: its concept's override, else its dimension's pillar."""
    entry = BY_ID.get(series_id)
    if entry is None:
        return None
    concept = SERIES_CONCEPTS.get((country, series_id))
    return CONCEPT_PILLAR.get(concept or "") or DIMENSION_PILLAR[entry.dimension]


def canonical_code(
    series_id: str, country: str, frequency: str, seasonal_adjustment: str
) -> str | None:
    """`<ISO3>.<PILLAR>.<INDICATOR>.<FREQ>.<ADJ>`, or None for a series outside the catalog."""
    concept = SERIES_CONCEPTS.get((country, series_id))
    pillar = pillar_for(country, series_id)
    place = COUNTRY_BY_ISO2.get(country)
    if concept is None or pillar is None:
        return None
    if place is None:
        raise TaxonomyError(f"Country {country!r} is not in the taxonomy: add it to COUNTRIES")
    return ".".join(
        (
            place.iso3,
            pillar,
            concept.upper(),
            frequency_code(frequency),
            adjustment_code(seasonal_adjustment),
        )
    )


def parse_code(code: str) -> tuple[str, str, str, str, str]:
    """Split a canonical code into (iso3, pillar, indicator, frequency, adjustment)."""
    parts = tuple(code.split("."))
    if len(parts) != 5 or not all(parts):
        raise TaxonomyError(f"{code!r} is not ISO3.PILLAR.INDICATOR.FREQ.ADJUSTMENT")
    return parts
