"""Official reserves excluding gold, in US dollars (P1-21): which economies, from which source.

FRED's copies of the IMF series where FRED carries them live with vintages (rule 17); the IMF
API for the rest. Checked 7 Nov 2026. Left out: China (last June 2026 on FRED and the IMF:
behind schedule), Hong Kong (last February 2024), the US (its own reserves do not gauge the
dollar) and the euro area (members report separately; the ECB's euro area reserves are a later
addition). Kept apart from the catalog so the cycle classification can use it too.
"""

# FRED series id -> country.
FRED_RESERVES: dict[str, str] = {
    f"TRESEG{iso2}M052N": iso2
    for iso2 in ("GB", "JP", "CA", "AU", "PL", "IN", "MX", "BR", "TR", "ZA", "KR", "SA")
}

# QuFin id -> IMF area, for the economies FRED does not carry.
IMF_RESERVES: dict[str, str] = {
    f"IMF_RES_{iso3}": iso3
    for iso3 in ("NZL", "CHE", "NOR", "SWE", "DNK", "CZE", "HUN", "SGP", "ARE")
}
IMF_ISO2 = {
    "NZL": "NZ",
    "CHE": "CH",
    "NOR": "NO",
    "SWE": "SE",
    "DNK": "DK",
    "CZE": "CZ",
    "HUN": "HU",
    "SGP": "SG",
    "ARE": "AE",
}

# Every reserves series -> country.
RESERVES: dict[str, str] = FRED_RESERVES | {k: IMF_ISO2[a] for k, a in IMF_RESERVES.items()}
