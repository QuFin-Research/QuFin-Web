"""Free daily reference prices behind each QuFin asset (backlog P1-25).

Each series is in the macro catalog (dimension "markets"), so it is loaded with its vintages,
checked against its release schedule and shown with its changes like any other series. The
values are reference prices (Fed H.10 noon buying rates in New York, EIA spot prices), not
tradable quotes: fine for daily history and backtests, not for execution or intraday use.
"""

PRICE_SERIES: dict[str, str] = {
    "EURUSD": "DEXUSEU",
    "GBPUSD": "DEXUSUK",
    "USDJPY": "DEXJPUS",
    "AUDUSD": "DEXUSAL",
    "NZDUSD": "DEXUSNZ",
    "USDCAD": "DEXCAUS",
    "USDCHF": "DEXSZUS",
    "WTI": "DCOILWTICO",
    "BRENT": "DCOILBRENTEU",
    "NATGAS": "DHHNGSP",
}

# QuFin assets without a free source that allows display in a paid product.
NO_FREE_SOURCE: dict[str, str] = {
    "XAUUSD": "LBMA gold was withdrawn from FRED; needs a licensed price feed",
    "XAGUSD": "No free daily source; needs a licensed price feed",
    "BTCUSD": "Coinbase data on FRED may not be reproduced; use exchange APIs after a terms check",
    "ETHUSD": "Coinbase data on FRED may not be reproduced; use exchange APIs after a terms check",
}
