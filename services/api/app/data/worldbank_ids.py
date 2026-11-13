"""World Bank annual indicators for the 50 economies added with the 85-country list (Rule J).

Probed on 13 Nov 2026 (one request per indicator and ten countries) and kept apart from the
catalog so the concepts, units and cycle classification can use it too. Four indicators, each a
different thing from what the monthly sources already give these countries (rules 16 and K):

- real GDP, constant 2015 US dollars (growth is derived from it, never stored beside it);
- unemployment, percent of the labour force (ILO modelled estimate);
- current account balance, percent of GDP (a new concept: the US series is an amount);
- trade balance, goods and services, current US dollars.

Not taken: consumer prices (the IMF has them monthly for most of these countries, rule K, and a
second copy would be a duplicate), and total reserves (the World Bank's include gold, the IMF's
reserves series do not: a different indicator). Only a country-indicator pair whose latest year is
2024 or later is listed: older annual data would fail the release check (rule 1). Liechtenstein
has only a 2015 GDP figure, so it has no series from this source; Isle of Man's latest GDP is 2023.
Annual data are not seasonally adjusted (there is no season to remove).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

HISTORY_START = date(1990, 1, 1)

# ISO3 -> ISO2 for the 50 economies (the taxonomy imports this module, so it cannot be used here).
ISO3_TO_ISO2: dict[str, str] = {
    "ALB": "AL",
    "AND": "AD",
    "ARM": "AM",
    "AUT": "AT",
    "AZE": "AZ",
    "BLR": "BY",
    "BEL": "BE",
    "BIH": "BA",
    "BRN": "BN",
    "BGR": "BG",
    "KHM": "KH",
    "CMR": "CM",
    "HRV": "HR",
    "CYP": "CY",
    "EGY": "EG",
    "EST": "EE",
    "FRO": "FO",
    "FIN": "FI",
    "GHA": "GH",
    "GRC": "GR",
    "ISL": "IS",
    "IRN": "IR",
    "IRL": "IE",
    "IMN": "IM",
    "ISR": "IL",
    "KEN": "KE",
    "XKX": "XK",
    "LVA": "LV",
    "LIE": "LI",
    "LTU": "LT",
    "LUX": "LU",
    "MKD": "MK",
    "MYS": "MY",
    "MLT": "MT",
    "MDA": "MD",
    "MCO": "MC",
    "MNE": "ME",
    "NLD": "NL",
    "NGA": "NG",
    "PRK": "KP",
    "PRT": "PT",
    "COG": "CG",
    "ROU": "RO",
    "SRB": "RS",
    "SVK": "SK",
    "SVN": "SI",
    "ESP": "ES",
    "UKR": "UA",
    "UZB": "UZ",
    "VEN": "VE",
}


@dataclass(frozen=True)
class WbIndicator:
    code: str  # World Bank indicator code
    key: str  # in the QuFin id: WB_<key>_<ISO3>
    concept: str
    title: str
    units: str
    unit_kind: str
    currency: str | None
    dimension: Literal["growth", "labour", "external"]
    cycle: Literal["leading", "coincident", "lagging"]
    cycle_reason: str
    change: Literal["pct", "diff"]
    countries: tuple[str, ...]


WB_INDICATORS: tuple[WbIndicator, ...] = (
    WbIndicator(
        "NY.GDP.MKTP.KD", "GDP", "real_gdp",
        "GDP (constant 2015 US$)", "Constant 2015 U.S. Dollars", "amount_currency", "USD",
        "growth", "coincident", "Output is the cycle itself: real GDP moves with it.", "pct",
        (
            "ALB", "AND", "ARM", "AUT", "AZE", "BEL", "BGR", "BIH", "BLR", "BRN", "CMR", "COG",
            "CYP", "EGY", "ESP", "EST", "FIN", "FRO", "GHA", "GRC", "HRV", "IRL", "IRN", "ISL",
            "ISR", "KEN", "KHM", "LTU", "LUX", "LVA", "MCO", "MDA", "MKD", "MLT", "MNE", "MYS",
            "NGA", "NLD", "PRT", "ROU", "SRB", "SVK", "SVN", "UKR", "UZB", "VEN", "XKX",
        ),
    ),
    WbIndicator(
        "SL.UEM.TOTL.ZS", "UNE", "unemployment_rate",
        "Unemployment, total (% of total labor force) (modeled ILO estimate)", "Percent",
        "rate_percent", None,
        "labour", "lagging", "Employers hire and fire after output has already turned.", "diff",
        (
            "ALB", "ARM", "AUT", "AZE", "BEL", "BGR", "BIH", "BLR", "BRN", "CMR", "COG", "CYP",
            "EGY", "ESP", "EST", "FIN", "GHA", "GRC", "HRV", "IRL", "IRN", "ISL", "ISR", "KEN",
            "KHM", "LTU", "LUX", "LVA", "MDA", "MKD", "MLT", "MNE", "MYS", "NGA", "NLD", "PRK",
            "PRT", "ROU", "SRB", "SVK", "SVN", "UZB", "VEN",
        ),
    ),
    WbIndicator(
        "BN.CAB.XOKA.GD.ZS", "CAB", "current_account_to_gdp",
        "Current account balance (% of GDP)", "Percent of GDP", "ratio", None,
        "external", "lagging", "Trade balances adjust after the cycle has turned.", "diff",
        (
            "ALB", "AND", "ARM", "AUT", "AZE", "BEL", "BGR", "BIH", "BLR", "BRN", "CMR", "CYP",
            "EGY", "ESP", "EST", "FIN", "GHA", "GRC", "HRV", "IRL", "ISL", "ISR", "KEN", "KHM",
            "LTU", "LUX", "LVA", "MDA", "MKD", "MLT", "MNE", "MYS", "NGA", "NLD", "PRT", "ROU",
            "SRB", "SVK", "SVN", "UKR", "UZB", "VEN", "XKX",
        ),
    ),
    WbIndicator(
        "NE.RSB.GNFS.CD", "TRD", "trade_balance",
        "External balance on goods and services (current US$)", "U.S. Dollars",
        "amount_currency", "USD",
        "external", "lagging", "Trade balances adjust after the cycle has turned.", "diff",
        (
            "ALB", "ARM", "AUT", "AZE", "BEL", "BGR", "BIH", "BLR", "BRN", "CMR", "COG", "CYP",
            "EGY", "ESP", "EST", "FIN", "FRO", "GHA", "GRC", "HRV", "IRL", "IRN", "ISL", "ISR",
            "KEN", "KHM", "LTU", "LUX", "LVA", "MDA", "MKD", "MLT", "MNE", "MYS", "NLD", "PRT",
            "ROU", "SRB", "SVK", "SVN", "UKR", "UZB", "VEN", "XKX",
        ),
    ),
)  # fmt: skip
WB_BY_CODE = {i.code: i for i in WB_INDICATORS}


@dataclass(frozen=True)
class WbSeries:
    id: str
    iso3: str
    iso2: str
    indicator: WbIndicator


WB_SERIES: tuple[WbSeries, ...] = tuple(
    WbSeries(f"WB_{i.key}_{c}", c, ISO3_TO_ISO2[c], i) for i in WB_INDICATORS for c in i.countries
)
WB_BY_ID = {s.id: s for s in WB_SERIES}
