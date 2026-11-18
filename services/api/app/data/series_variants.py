"""The definition behind an indicator's one global name (rule 18).

Every country's consumer prices are shown as "CPI", but the measures differ: the euro area's
HICP, the United States' CPI-U and a national statistics office's own CPI cover different
baskets. A series records its `variant`; the tooltip shows it and a comparison across variants
carries a notice (rules 10 and 23). Only concepts whose definitions differ between sources need
one; `VARIANT_CONCEPTS` lists them, and `tests/test_indicator_concepts.py` fails if a series of
such a concept has none.

The variant of the IMF and BIS series is the national definition each country reports to them,
not checked country by country (assumptions register, section 4q).
"""

from app.data.indicator_concepts import SERIES_CONCEPTS

NATIONAL_CPI = "National CPI"
NATIONAL_CORE_CPI = "National core CPI"

VARIANT_CONCEPTS = frozenset({"consumer_prices", "core_consumer_prices"})

# Series whose definition is known from the producer's own notes.
_KNOWN: dict[str, str] = {
    "CPIAUCSL": "CPI-U, all items",  # BLS, all urban consumers
    "CPILFESL": "CPI-U, excluding food and energy",
    "CP0000PTM086NEST": "HICP, all items",  # FRED's copy of Eurostat's HICP
    "HICP.M.U2.N.000000.4D0.ANR": "HICP, all items",  # ECB, euro area
    "HICP.M.U2.N.XEF000.4D0.ANR": "HICP, excluding energy, food, alcohol and tobacco",
    "ESTAT_CORE_DE": "HICP, excluding energy, food, alcohol and tobacco",
    "ESTAT_CORE_FR": "HICP, excluding energy, food, alcohol and tobacco",
    "ESTAT_CORE_IT": "HICP, excluding energy, food, alcohol and tobacco",
    "ONS_DKO8": "CPI, excluding energy, food, alcohol and tobacco",  # ONS
}


def variant_of(series_id: str, country: str) -> str | None:
    """The definition of a series of a concept that has variants; None for any other series."""
    concept = SERIES_CONCEPTS.get((country, series_id))
    if concept not in VARIANT_CONCEPTS:
        return None
    if series_id in _KNOWN:
        return _KNOWN[series_id]
    if series_id.startswith(("IMF_CPI_", "BIS_CPI_")):
        return NATIONAL_CPI
    return None


def variant_notice(concept_name: str, variants: set[str]) -> str | None:
    """The notice for a comparison whose series follow different definitions."""
    if len(variants) < 2:
        return None
    return (
        f"These {concept_name} series follow different definitions ("
        + "; ".join(sorted(variants))
        + "): their coverage differs, so compare levels with care."
    )
