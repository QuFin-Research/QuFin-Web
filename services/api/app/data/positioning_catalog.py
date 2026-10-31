"""CFTC futures contracts behind each QuFin asset (Commitments of Traders, legacy report).

`sign` turns the contract's positioning into the asset's direction: the CME yen future is long
JPY, which is short USDJPY.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CotContract:
    symbol: str
    code: str
    sign: int


COT_CONTRACTS: tuple[CotContract, ...] = (
    CotContract("EURUSD", "099741", 1),  # Euro FX, CME
    CotContract("GBPUSD", "096742", 1),  # British pound, CME
    CotContract("USDJPY", "097741", -1),  # Japanese yen, CME (long JPY = short USDJPY)
    CotContract("AUDUSD", "232741", 1),  # Australian dollar, CME
    CotContract("XAUUSD", "088691", 1),  # Gold, COMEX
    CotContract("XAGUSD", "084691", 1),  # Silver, COMEX
    CotContract("WTI", "067651", 1),  # WTI physical, NYMEX
    CotContract("BRENT", "06765T", 1),  # Brent last day, NYMEX
    CotContract("NATGAS", "023651", 1),  # Henry Hub natural gas, NYMEX
    CotContract("BTCUSD", "133741", 1),  # Bitcoin, CME
    CotContract("ETHUSD", "146021", 1),  # Ether cash settled, CME
)

BY_SYMBOL = {c.symbol: c for c in COT_CONTRACTS}
BY_CODE = {c.code: c for c in COT_CONTRACTS}

DEFAULT_COT_START = date(2015, 1, 1)
