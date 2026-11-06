"""Declared unit kind and currency of every catalog series (rule 23).

Reviewed by a person, never generated at run time. Each entry was first derived from the units
the source states (FRED `units`, ECB UNIT and UNIT_MULT, OECD measure, EIA and Treasury field
definitions) by `app.domain.units.classify`, then checked; the trailing comment is that units
text. Every ingest derives the pair again from the source's metadata, and the release check marks
a series "review" if it no longer matches this declaration. A new series is added here before it
is loaded; `unknown` fails the tests until a person decides.
"""

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
}
