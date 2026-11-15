"""Fifteen benchmark G20 and GCC indicators the taxonomy is checked against.

Each is a series QuFin already loads from its real source (nothing here is typed in or sample
data): the policy rate and the price, labour and growth anchors for the United States, the euro
area, the United Kingdom, Japan, China, India and Brazil, and the two Saudi Arabian series the
BIS carries. `python -m app.cli seed-benchmarks` codes them, then reports each one's latest
period and value, and fails if one has not been loaded. Saudi Arabia has only these two until
the central-bank connectors (backlog P1-24) are built.
"""

BENCHMARK_SERIES: tuple[str, ...] = (
    "FEDFUNDS",  # USA policy rate
    "CPIAUCSL",  # USA consumer prices
    "UNRATE",  # USA unemployment rate
    "GDPC1",  # USA real GDP
    "DGS2",  # USA 2-year Treasury yield
    "FM.D.U2.EUR.4F.KR.DFR.LEV",  # Euro area ECB deposit facility rate
    "HICP.M.U2.N.000000.4D0.ANR",  # Euro area consumer prices (HICP)
    "BIS_CBPOL_GB",  # United Kingdom policy rate
    "BIS_CBPOL_JP",  # Japan policy rate
    "OECD_CLI_JPN",  # Japan composite leading indicator
    "BIS_CBPOL_CN",  # China policy rate
    "BIS_CBPOL_IN",  # India policy rate
    "BIS_CBPOL_BR",  # Brazil policy rate
    "BIS_CBPOL_SA",  # Saudi Arabia policy rate (GCC)
    "BIS_REER_SA",  # Saudi Arabia real effective exchange rate (GCC)
)
