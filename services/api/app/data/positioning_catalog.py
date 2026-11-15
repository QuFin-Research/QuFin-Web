"""CFTC futures contracts behind each QuFin asset (Commitments of Traders).

Each contract comes from exactly one CFTC report, so the same positions are never stored twice:
financial futures (currencies, the US Dollar Index, crypto) from Traders in Financial Futures,
read through leveraged funds (hedge funds and CTAs); commodities, which that report does not
cover, from the legacy report, read through non-commercial traders (large speculators).

`sign` turns the contract's positioning into the asset's direction: the CME yen future is long
JPY, which is short USDJPY.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Report = Literal["legacy", "tff"]

# Whose net position each report's metrics follow.
GROUPS: dict[Report, str] = {
    "legacy": "Non-commercial traders (large speculators)",
    "tff": "Leveraged funds (hedge funds and CTAs)",
}


@dataclass(frozen=True)
class CotContract:
    symbol: str
    code: str
    sign: int
    report: Report = "legacy"
    # Shown with the data when the contract is only a partial view of the market.
    caveat: str | None = None


COT_CONTRACTS: tuple[CotContract, ...] = (
    # --- Traders in Financial Futures -------------------------------------------------------
    CotContract("EURUSD", "099741", 1, "tff"),  # Euro FX, CME
    CotContract("GBPUSD", "096742", 1, "tff"),  # British pound, CME
    CotContract("USDJPY", "097741", -1, "tff"),  # Japanese yen, CME (long JPY = short USDJPY)
    CotContract("AUDUSD", "232741", 1, "tff"),  # Australian dollar, CME
    CotContract("USDCAD", "090741", -1, "tff"),  # Canadian dollar, CME (long CAD = short USDCAD)
    CotContract("USDCHF", "092741", -1, "tff"),  # Swiss franc, CME (long CHF = short USDCHF)
    CotContract("NZDUSD", "112741", 1, "tff"),  # New Zealand dollar, CME
    CotContract(
        "USDX",
        "098662",
        1,
        "tff",
        caveat=(
            "ICE US Dollar Index futures (six currencies, mostly the euro). QuFin has no "
            "licensed price for this index; the Fed's broad dollar index (DTWEXBGS) is a "
            "different, trade-weighted basket of 26 currencies."
        ),
    ),
    CotContract("BTCUSD", "133741", 1, "tff"),  # Bitcoin, CME
    CotContract("ETHUSD", "146021", 1, "tff"),  # Ether cash settled, CME
    # --- Legacy report (commodities) ----------------------------------------------------------
    CotContract("XAUUSD", "088691", 1),  # Gold, COMEX
    CotContract("XAGUSD", "084691", 1),  # Silver, COMEX
    CotContract("WTI", "067651", 1),  # WTI physical, NYMEX
    CotContract(
        "BRENT",
        "06765T",
        1,
        caveat=(
            "NYMEX Brent Last Day futures only. Most Brent trading is on ICE Futures "
            "Europe, which the CFTC does not report, so this is a small, partial view "
            "of Brent positioning (open interest about an eighth of NYMEX WTI's)."
        ),
    ),
    CotContract("NATGAS", "023651", 1),  # Henry Hub natural gas, NYMEX
)

BY_SYMBOL = {c.symbol: c for c in COT_CONTRACTS}
BY_CODE = {c.code: c for c in COT_CONTRACTS}

DEFAULT_COT_START = date(2015, 1, 1)
