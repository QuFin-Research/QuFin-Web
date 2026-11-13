"""Declared unit kind and currency of every catalog series (rule 23).

Reviewed by a person, never generated at run time. Each entry was first derived from the units
the source states (FRED `units`, ECB UNIT and UNIT_MULT, OECD measure, EIA and Treasury field
definitions) by `app.domain.units.classify`, then checked; the trailing comment is that units
text. Every ingest derives the pair again from the source's metadata, and the release check marks
a series "review" if it no longer matches this declaration. A new series is added here before it
is loaded; `unknown` fails the tests until a person decides.
"""

from app.data.bis_ids import BIS_SERIES
from app.data.gap_ids import EUROSTAT_SERIES, FRED_ADDITIONS, ONS_SERIES
from app.data.macro_ids import IMF_CPI, OECD_MACRO
from app.data.reserves_ids import FRED_RESERVES, IMF_RESERVES
from app.data.worldbank_ids import WB_SERIES

# Series id -> (unit kind, ISO currency or None for dimensionless).
SERIES_UNITS: dict[str, tuple[str, str | None]] = {
    "AWHMAN": ("other", None),  # Hours
    "ICSA": ("count", None),  # Number
    "ACOGNO": ("amount_currency", "USD"),  # Millions of Dollars
    "NEWORDER": ("amount_currency", "USD"),  # Millions of Dollars
    "NOCDFSA066MSFRBPHI": ("index", None),  # Index
    "GACDISA066MSFRBNY": ("index", None),  # Index
    "BACTSAMFRBDAL": ("index", None),  # Index
    "PERMIT": ("count", None),  # Thousands of Units
    "HOUST": ("count", None),  # Thousands of Units
    "HSN1F": ("count", None),  # Thousands
    "TEMPHELPS": ("count", None),  # Thousands of Persons
    "JTSJOL": ("count", None),  # Level in Thousands
    "JTSQUR": ("rate_percent", None),  # Rate
    "T10YFF": ("rate_percent", None),  # Percent
    "T10Y3M": ("rate_percent", None),  # Percent
    "NFCI": ("index", None),  # Index
    "STLFSI4": ("index", None),  # Index
    "USALOLITOAASTSAM": ("index", None),  # Index
    "UMCSENT": ("index", None),  # Index 1966:Q1=100
    "GDPC1": ("amount_currency", "USD"),  # Billions of Chained 2017 Dollars
    "WEI": ("index", None),  # Index
    "INDPRO": ("index", None),  # Index 2017=100
    "RRSFS": ("amount_currency", "USD"),  # Millions of 1982-84 CPI Adjusted Dollars
    "W875RX1": ("amount_currency", "USD"),  # Billions of Chained 2017 Dollars
    "PCEC96": ("amount_currency", "USD"),  # Billions of Chained 2017 Dollars
    "PI": ("amount_currency", "USD"),  # Billions of Dollars
    "PAYEMS": ("count", None),  # Thousands of Persons
    "UEMPMEAN": ("other", None),  # Weeks
    "UNRATE": ("rate_percent", None),  # Percent
    "CCSA": ("count", None),  # Number
    "ISRATIO": ("ratio", None),  # Ratio
    "ULCMFG": ("index", None),  # Index 2017=100
    "CUSR0000SAS": ("index", None),  # Index 1982-1984=100
    "CPILFESL": ("index", None),  # Index 1982-1984=100
    "BUSLOANS": ("amount_currency", "USD"),  # Billions of U.S. Dollars
    "TOTALSL": ("amount_currency", "USD"),  # Millions of U.S. Dollars
    "CPIAUCSL": ("index", None),  # Index 1982-1984=100
    "GASREGW": ("price_per_unit", "USD"),  # Dollars per Gallon
    "PCEPILFE": ("index", None),  # Index 2017=100
    "PPIFIS": ("index", None),  # Index Nov 2009=100
    "CP": ("amount_currency", "USD"),  # Billions of Dollars
    "T10YIE": ("rate_percent", None),  # Percent
    "FEDFUNDS": ("rate_percent", None),  # Percent
    "DGS2": ("rate_percent", None),  # Percent
    "DFII10": ("rate_percent", None),  # Percent
    "WALCL": ("amount_currency", "USD"),  # Millions of U.S. Dollars
    "M2SL": ("amount_currency", "USD"),  # Billions of Dollars
    "BAA10Y": ("rate_percent", None),  # Percent
    "BOPGSTB": ("amount_currency", "USD"),  # Millions of Dollars
    "IEABC": ("amount_currency", "USD"),  # Millions of Dollars
    "MTSDS133FMS": ("amount_currency", "USD"),  # Millions of Dollars
    "GFDEGDQ188S": ("ratio", None),  # Percent of GDP
    "TREAS_DEBT_TOTAL": ("amount_currency", "USD"),  # Dollars
    "TREAS_AVG_RATE_MARKETABLE": ("rate_percent", None),  # Percent
    "TREAS_INTEREST_EXPENSE": ("amount_currency", "USD"),  # Dollars
    "WCESTUS1": ("other", None),  # Thousand Barrels
    "W_EPC0_SAX_YCUOK_MBBL": ("other", None),  # Thousand Barrels
    "WCSSTUS1": ("other", None),  # Thousand Barrels
    "WCRFPUS2": ("other", None),  # Thousand Barrels per Day
    "WPULEUS3": ("rate_percent", None),  # Percent
    "WGTSTUS1": ("other", None),  # Thousand Barrels
    "WDISTUS1": ("other", None),  # Thousand Barrels
    "WCRIMUS2": ("other", None),  # Thousand Barrels per Day
    "WCREXUS2": ("other", None),  # Thousand Barrels per Day
    "WRPUPUS2": ("other", None),  # Thousand Barrels per Day
    "WGFUPUS2": ("other", None),  # Thousand Barrels per Day
    "WDIUPUS2": ("other", None),  # Thousand Barrels per Day
    "FM.D.U2.EUR.4F.KR.DFR.LEV": ("rate_percent", None),  # Percent per annum
    "HICP.M.U2.N.000000.4D0.ANR": ("rate_percent", None),  # Percentage change
    "HICP.M.U2.N.XEF000.4D0.ANR": ("rate_percent", None),  # Percentage change
    "BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E": ("amount_currency", "EUR"),  # Millions of Euro
    "OECD_CLI_GBR": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_JPN": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_CAN": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_AUS": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_MEX": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_TUR": ("index", None),  # Index, long-term average = 100
    "OECD_CLI_KOR": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_GBR": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_JPN": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_AUS": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_NZL": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_CHE": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_SWE": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_DNK": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_CZE": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_HUN": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_POL": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_MEX": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_TUR": ("index", None),  # Index, long-term average = 100
    "OECD_BCI_KOR": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_GBR": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_JPN": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_CAN": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_AUS": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_NZL": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_POL": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_MEX": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_TUR": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_CHE": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_SWE": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_DNK": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_CZE": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_HUN": ("index", None),  # Index, long-term average = 100
    "OECD_CCI_KOR": ("index", None),  # Index, long-term average = 100
    "DEXUSEU": ("price_per_unit", "USD"),  # U.S. Dollars to One Euro
    "DEXUSUK": ("price_per_unit", "USD"),  # U.S. Dollars to One U.K. Pound Sterling
    "DEXJPUS": ("price_per_unit", "JPY"),  # Japanese Yen to One U.S. Dollar
    "DEXUSAL": ("price_per_unit", "USD"),  # U.S. Dollars to One Australian Dollar
    "DEXUSNZ": ("price_per_unit", "USD"),  # U.S. Dollars to One New Zealand Dollar
    "DEXCAUS": ("price_per_unit", "CAD"),  # Canadian Dollars to One U.S. Dollar
    "DEXSZUS": ("price_per_unit", "CHF"),  # Swiss Francs to One U.S. Dollar
    "DCOILWTICO": ("price_per_unit", "USD"),  # Dollars per Barrel
    "DCOILBRENTEU": ("price_per_unit", "USD"),  # Dollars per Barrel
    "DHHNGSP": ("price_per_unit", "USD"),  # Dollars per Million BTU
    "DTWEXBGS": ("index", None),  # Index Jan 2006=100
    "TRESEGGBM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGJPM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGCAM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGAUM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGPLM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGINM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGMXM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGBRM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGTRM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGZAM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGKRM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "TRESEGSAM052N": ("amount_currency", "USD"),  # Millions of Dollars (FRED)
    "IMF_RES_NZL": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_CHE": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_NOR": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_SWE": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_DNK": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_CZE": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_HUN": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_SGP": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "IMF_RES_ARE": ("amount_currency", "USD"),  # U.S. Dollars (IMF UNIT=USD, in units)
    "BIS_CBPOL_GB": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_JP": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_CA": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_AU": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_NZ": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_CH": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_NO": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_SE": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_DK": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_CZ": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_HU": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_PL": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_CN": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_IN": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_MX": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_BR": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_TR": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_ZA": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_HK": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_KR": ("rate_percent", None),  # Percent per annum
    "BIS_CBPOL_SA": ("rate_percent", None),  # Percent per annum
    "BIS_NEER_GB": ("index", None),  # Index, 2020=100
    "BIS_NEER_JP": ("index", None),  # Index, 2020=100
    "BIS_NEER_CA": ("index", None),  # Index, 2020=100
    "BIS_NEER_AU": ("index", None),  # Index, 2020=100
    "BIS_NEER_NZ": ("index", None),  # Index, 2020=100
    "BIS_NEER_CH": ("index", None),  # Index, 2020=100
    "BIS_NEER_NO": ("index", None),  # Index, 2020=100
    "BIS_NEER_SE": ("index", None),  # Index, 2020=100
    "BIS_NEER_DK": ("index", None),  # Index, 2020=100
    "BIS_NEER_CZ": ("index", None),  # Index, 2020=100
    "BIS_NEER_HU": ("index", None),  # Index, 2020=100
    "BIS_NEER_PL": ("index", None),  # Index, 2020=100
    "BIS_NEER_CN": ("index", None),  # Index, 2020=100
    "BIS_NEER_IN": ("index", None),  # Index, 2020=100
    "BIS_NEER_MX": ("index", None),  # Index, 2020=100
    "BIS_NEER_BR": ("index", None),  # Index, 2020=100
    "BIS_NEER_TR": ("index", None),  # Index, 2020=100
    "BIS_NEER_ZA": ("index", None),  # Index, 2020=100
    "BIS_NEER_HK": ("index", None),  # Index, 2020=100
    "BIS_NEER_KR": ("index", None),  # Index, 2020=100
    "BIS_NEER_SA": ("index", None),  # Index, 2020=100
    "BIS_NEER_XM": ("index", None),  # Index, 2020=100
    "BIS_NEER_SG": ("index", None),  # Index, 2020=100
    "BIS_NEER_AE": ("index", None),  # Index, 2020=100
    "BIS_REER_GB": ("index", None),  # Index, 2020=100
    "BIS_REER_JP": ("index", None),  # Index, 2020=100
    "BIS_REER_CA": ("index", None),  # Index, 2020=100
    "BIS_REER_AU": ("index", None),  # Index, 2020=100
    "BIS_REER_NZ": ("index", None),  # Index, 2020=100
    "BIS_REER_CH": ("index", None),  # Index, 2020=100
    "BIS_REER_NO": ("index", None),  # Index, 2020=100
    "BIS_REER_SE": ("index", None),  # Index, 2020=100
    "BIS_REER_DK": ("index", None),  # Index, 2020=100
    "BIS_REER_CZ": ("index", None),  # Index, 2020=100
    "BIS_REER_HU": ("index", None),  # Index, 2020=100
    "BIS_REER_PL": ("index", None),  # Index, 2020=100
    "BIS_REER_CN": ("index", None),  # Index, 2020=100
    "BIS_REER_IN": ("index", None),  # Index, 2020=100
    "BIS_REER_MX": ("index", None),  # Index, 2020=100
    "BIS_REER_BR": ("index", None),  # Index, 2020=100
    "BIS_REER_TR": ("index", None),  # Index, 2020=100
    "BIS_REER_ZA": ("index", None),  # Index, 2020=100
    "BIS_REER_HK": ("index", None),  # Index, 2020=100
    "BIS_REER_KR": ("index", None),  # Index, 2020=100
    "BIS_REER_SA": ("index", None),  # Index, 2020=100
    "BIS_REER_XM": ("index", None),  # Index, 2020=100
    "BIS_REER_SG": ("index", None),  # Index, 2020=100
    "BIS_REER_AE": ("index", None),  # Index, 2020=100
    "BIS_CREDIT_GB": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_JP": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_CA": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_AU": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_NZ": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_CH": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_NO": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_SE": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_DK": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_CZ": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_HU": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_PL": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_CN": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_IN": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_MX": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_BR": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_TR": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_ZA": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_HK": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_KR": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_SA": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_XM": ("ratio", None),  # Percent of GDP
    "BIS_CREDIT_SG": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_GB": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_JP": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_CA": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_AU": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_NZ": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_CH": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_NO": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_SE": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_DK": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_CZ": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_HU": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_PL": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_CN": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_IN": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_MX": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_BR": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_TR": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_ZA": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_HK": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_KR": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_SA": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_XM": ("ratio", None),  # Percent of GDP
    "BIS_CREDGAP_SG": ("ratio", None),  # Percent of GDP
    "ECIALLCIV": ("index", None),  # Index, Dec 2005=100 (BLS ECI, via FRED)
}

# Consumer prices (IMF, annual rate of change) and unemployment (OECD, percent of the labour force)
# by country (P1-23); the units text each source states is in the comment.
SERIES_UNITS |= {series_id: ("rate_percent", None) for series_id in IMF_CPI}  # Percentage change
SERIES_UNITS |= {series_id: ("rate_percent", None) for series_id in OECD_MACRO}  # Percent

# Coverage-gap series (Sprints 1-4): each source's own units text is in `gap_ids.py`.
SERIES_UNITS |= {a.id: (a.unit_kind, a.currency) for a in FRED_ADDITIONS}
SERIES_UNITS |= {s.id: (s.unit_kind, s.currency) for s in ONS_SERIES}
SERIES_UNITS |= {e.id: (e.unit_kind, None) for e in EUROSTAT_SERIES}
SERIES_UNITS |= {w.id: (w.indicator.unit_kind, w.indicator.currency) for w in WB_SERIES}
_BIS_UNITS = {
    "CBPOL": ("rate_percent", None),  # Percent per annum
    "NEER": ("index", None),  # Index, 2020=100
    "REER": ("index", None),  # Index, 2020=100
    "CREDIT": ("ratio", None),  # Percent of GDP
    "CREDGAP": ("ratio", None),  # Percent of GDP
    "SPP": ("index", None),  # Index, 2010=100
}
for _series_id, (_code, _area) in BIS_SERIES.items():
    SERIES_UNITS.setdefault(_series_id, _BIS_UNITS[_code])
for _series_id in (*IMF_RESERVES, *FRED_RESERVES):
    SERIES_UNITS.setdefault(
        _series_id, ("amount_currency", "USD")
    )  # Millions or units of US dollars
for _area in ("DEU", "FRA", "ITA"):
    for _measure in ("CLI", "BCI", "CCI"):
        SERIES_UNITS.setdefault(f"OECD_{_measure}_{_area}", ("index", None))  # long-term avg = 100
