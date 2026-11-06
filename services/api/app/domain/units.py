"""Unit kind and currency of a series, read from the source's own units text (rule 23).

Each source states its units (FRED's `units`, the ECB's UNIT and UNIT_MULT, the OECD measure,
EIA and Treasury field definitions). `classify` reads that text; it never guesses, and returns
"unknown" when the text does not say. `comparable` says whether two series can share one scale
as actual values; otherwise they need a common basis first.
"""

import re
from dataclasses import dataclass
from typing import Literal

UnitKind = Literal[
    "amount_currency",
    "count",
    "index",
    "rate_percent",
    "ratio",
    "price_per_unit",
    "other",
    "unknown",
]
UNIT_KINDS: tuple[str, ...] = UnitKind.__args__  # type: ignore[attr-defined]

# Currency names as the sources write them, longest first so "U.S. Dollars" wins over "Dollars".
_CURRENCIES = (
    ("u.k. pound sterling", "GBP"),
    ("new zealand dollar", "NZD"),
    ("australian dollar", "AUD"),
    ("canadian dollar", "CAD"),
    ("japanese yen", "JPY"),
    ("swiss franc", "CHF"),
    ("u.s. dollar", "USD"),
    ("us dollar", "USD"),
    ("euro", "EUR"),
)
_SCALE = re.compile(r"^(level in )?(thousands?|millions?|billions?|trillions?)( of)?\s*")
_FX = re.compile(r"^(.+?) to one (.+)$")


@dataclass(frozen=True)
class UnitInfo:
    kind: UnitKind
    currency: str | None
    # The unit without its scale ("Millions of Dollars" and "Billions of Dollars" share "dollars"):
    # two series with the same kind, currency and basis can share one scale once rescaled.
    basis: str


def _currency(text: str, country: str) -> str | None:
    for name, code in _CURRENCIES:
        if name in text:
            return code
    # An unqualified "dollars" is the series' own country's currency only for the US.
    if "dollar" in text and country == "US":
        return "USD"
    return None


def classify(units: str, country: str) -> UnitInfo:
    text = units.strip().lower()
    basis = _SCALE.sub("", text).replace("u.s. dollars", "dollars")
    if m := _FX.match(text):  # "Canadian Dollars to One U.S. Dollar": CAD per USD
        price, per = _currency(m[1], ""), _currency(m[2], "")
        if price and per:
            return UnitInfo("price_per_unit", price, f"{price.lower()} per {per.lower()}")
        return UnitInfo("unknown", None, basis)
    if text.startswith("index"):
        return UnitInfo("index", None, basis)
    if text in {"percent", "percent per annum", "percentage change", "rate"}:
        return UnitInfo("rate_percent", None, "percent")
    if text.startswith("percent of "):
        return UnitInfo("ratio", None, basis)
    if text == "ratio":
        return UnitInfo("ratio", None, basis)
    if " per " in text and "dollar" in text:  # "Dollars per Barrel"
        currency = _currency(text, country)
        return UnitInfo("price_per_unit" if currency else "unknown", currency, basis)
    if "dollar" in text or "euro" in text:
        currency = _currency(text, country)
        return UnitInfo("amount_currency" if currency else "unknown", currency, basis)
    if basis in {"persons", "units", "number", ""} or text in {"thousands", "level in thousands"}:
        return UnitInfo("count", None, basis or "number")
    if "barrels" in text or text in {"hours", "weeks"}:
        return UnitInfo("other", None, basis)
    return UnitInfo("unknown", None, basis)


@dataclass(frozen=True)
class Comparison:
    same_scale: bool
    reason: str


def comparable(a: UnitInfo, b: UnitInfo) -> Comparison:
    """Whether two series can share one scale as actual values (rule 23).

    They can only with the same unit kind, the same currency and the same unit basis. An index
    needs a stated base (an unlabelled "Index" is a diffusion or standardised reading); anything
    else needs a common basis first: percent or point changes, standardised scores, a ratio to a
    common denominator, indexes rebased to one date, or conversion at a stated exchange rate.
    """
    if "unknown" in (a.kind, b.kind):
        return Comparison(False, "a unit is unknown: decide it before comparing")
    if a.kind != b.kind:
        return Comparison(False, f"different kinds ({a.kind} vs {b.kind}): use a common basis")
    if a.currency != b.currency:
        return Comparison(
            False, f"different currencies ({a.currency} vs {b.currency}): convert at a stated rate"
        )
    if a.kind == "index" and ("=" not in a.basis or a.basis != b.basis):
        return Comparison(False, "indexes without the same stated base: rebase or standardise")
    if a.kind == "count" and a.basis == "number":
        # "Number" or "Thousands" does not say what is counted (claims, homes, job openings).
        return Comparison(False, "counts of unstated things: use a common basis")
    if a.basis != b.basis:
        return Comparison(False, f"different units ({a.basis} vs {b.basis}): use a common basis")
    return Comparison(True, "same unit and currency")
