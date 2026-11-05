"""Indicator concepts: the human-readable name every user sees, shared across countries.

A concept is what an indicator measures, independent of who publishes it: "unemployment_rate"
is the US UNRATE today and the UK's ONS series later, both shown as "Unemployment Rate", so
economies can be compared side by side. Rules (services/api/CLAUDE.md, rules 16-18):

- every catalog series maps to exactly one concept, and a country has at most one series per
  concept: no duplicated indicators;
- names are short and plain; the explanation is one sentence for a general visitor; the
  official title and source code stay available to professionals (tooltip);
- a series that can be derived from stored ones is not stored (REDUNDANT below).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    name: str
    explanation: str


CONCEPTS: dict[str, Concept] = {
    # --- Labour -------------------------------------------------------------------------------
    "factory_workweek": Concept(
        "Factory Workweek",
        "Average weekly hours of factory workers; employers trim hours before they cut jobs.",
    ),
    "initial_jobless_claims": Concept(
        "Initial Jobless Claims",
        "New claims for unemployment benefits each week; a rise signals layoffs.",
    ),
    "continuing_jobless_claims": Concept(
        "Continuing Jobless Claims",
        "People still receiving unemployment benefits; shows how hard it is to find work.",
    ),
    "temporary_staffing_jobs": Concept(
        "Temporary Staffing Jobs",
        "Temporary workers are hired first in upturns and let go first in downturns.",
    ),
    "job_openings": Concept(
        "Job Openings",
        "Positions employers are trying to fill; a measure of demand for workers.",
    ),
    "quit_rate": Concept(
        "Quit Rate",
        "Share of workers leaving their jobs each month; high when they expect to find better.",
    ),
    "nonfarm_payrolls": Concept(
        "Nonfarm Payrolls",
        "Number of jobs outside farming; the headline monthly jobs figure.",
    ),
    "unemployment_rate": Concept(
        "Unemployment Rate",
        "Share of people who want a job and are looking but do not have one.",
    ),
    "unemployment_duration": Concept(
        "Unemployment Duration",
        "Average weeks the unemployed have been out of work; it turns after the economy does.",
    ),
    # --- Growth -------------------------------------------------------------------------------
    "consumer_goods_orders": Concept(
        "Consumer Goods Orders",
        "New orders placed with factories for consumer goods.",
    ),
    "core_capital_goods_orders": Concept(
        "Business Investment Orders",
        "Orders for business equipment, excluding aircraft and defence: investment plans.",
    ),
    "manufacturing_new_orders_survey": Concept(
        "Factory New Orders Survey",
        "Share of surveyed factories reporting more orders minus those reporting fewer.",
    ),
    "building_permits": Concept(
        "Building Permits",
        "Permits issued for new homes: construction plans before work starts.",
    ),
    "housing_starts": Concept(
        "Housing Starts",
        "New homes on which construction began this month.",
    ),
    "new_home_sales": Concept(
        "New Home Sales",
        "Sales of newly built homes; they react quickly to mortgage rates.",
    ),
    "real_gdp": Concept(
        "Real GDP",
        "The economy's total output after inflation; the broadest measure of growth.",
    ),
    "weekly_economic_index": Concept(
        "Weekly Economic Index",
        "Weekly activity index scaled to GDP growth; the earliest read on the economy.",
    ),
    "industrial_production": Concept(
        "Industrial Production",
        "Output of factories, mines and utilities.",
    ),
    "real_retail_sales": Concept(
        "Real Retail Sales",
        "Shop and restaurant sales after inflation.",
    ),
    "real_consumer_spending": Concept(
        "Real Consumer Spending",
        "Household spending after inflation; the largest part of the economy.",
    ),
    "personal_income": Concept(
        "Personal Income",
        "Total household income before inflation, including government payments.",
    ),
    "real_income_excl_transfers": Concept(
        "Real Income excl. Transfers",
        "Household income after inflation, without government payments: earned income.",
    ),
    "corporate_profits": Concept(
        "Corporate Profits",
        "Companies' after-tax profits, which fund investment and hiring.",
    ),
    "inventories_to_sales": Concept(
        "Inventories-to-Sales Ratio",
        "Months of stock on hand; it rises when sales slow down.",
    ),
    # --- Inflation ----------------------------------------------------------------------------
    "consumer_prices": Concept(
        "Consumer Prices",
        "Change in the prices households pay for a typical basket of goods and services.",
    ),
    "core_consumer_prices": Concept(
        "Core Consumer Prices",
        "Consumer prices excluding volatile food and energy: underlying inflation.",
    ),
    "services_prices": Concept(
        "Services Prices",
        "Prices of services such as rent, healthcare and travel; slow to turn, wage-driven.",
    ),
    "core_pce_prices": Concept(
        "Core PCE Prices",
        "The central bank's preferred inflation measure, excluding food and energy.",
    ),
    "producer_prices": Concept(
        "Producer Prices",
        "Prices businesses receive for their output; they feed through to consumer prices.",
    ),
    "unit_labour_costs": Concept(
        "Unit Labour Costs",
        "Wage cost to produce one unit of output; rising costs push prices up.",
    ),
    "inflation_expectations_10y": Concept(
        "Inflation Expectations (10-Year)",
        "Average inflation bond markets expect over the next ten years.",
    ),
    "gasoline_price": Concept(
        "Gasoline Price",
        "Weekly average pump price; the earliest read on consumer prices.",
    ),
    # --- Monetary policy, rates and credit -----------------------------------------------------
    "policy_rate": Concept(
        "Policy Interest Rate",
        "The central bank's overnight rate, which sets the cost of money.",
    ),
    "yield_2y": Concept(
        "2-Year Bond Yield",
        "Government 2-year borrowing cost; tracks where markets expect policy rates to go.",
    ),
    "real_yield_10y": Concept(
        "Real 10-Year Yield",
        "10-year yield after expected inflation; a key driver of gold and the currency.",
    ),
    "yield_curve_10y_3m": Concept(
        "Yield Curve (10y minus 3m)",
        "Long minus short rates; when it turns negative, a recession has often followed.",
    ),
    "long_rate_vs_policy_rate": Concept(
        "Long Rate vs Policy Rate",
        "10-year yield minus the policy rate; low or negative means policy is tight.",
    ),
    "central_bank_balance_sheet": Concept(
        "Central Bank Balance Sheet",
        "Assets held by the central bank; growth adds liquidity, shrinking removes it.",
    ),
    "money_supply": Concept(
        "Broad Money Supply",
        "Cash, deposits and savings (M2 in the US, M3 in the euro area); growth fuels spending.",
    ),
    "business_loans": Concept(
        "Business Loans",
        "Bank loans to companies outstanding; they keep growing late into an upturn.",
    ),
    "consumer_credit": Concept(
        "Consumer Credit",
        "Household debt such as cards and car loans outstanding.",
    ),
    # --- Sentiment and financial conditions ----------------------------------------------------
    "consumer_sentiment": Concept(
        "Consumer Sentiment",
        "How confident households feel about their finances and the economy.",
    ),
    "financial_conditions": Concept(
        "Financial Conditions",
        "How easy it is to borrow and invest; positive means tighter than average.",
    ),
    "financial_stress": Concept(
        "Financial Stress",
        "Strain in funding and credit markets; above zero means more stress than usual.",
    ),
    "corporate_credit_spread": Concept(
        "Corporate Credit Spread",
        "Extra yield companies pay over government bonds; it widens when investors worry.",
    ),
    "trade_weighted_currency": Concept(
        "Trade-Weighted Currency",
        "The currency's value against a basket of trading partners' currencies.",
    ),
    # --- External and fiscal -------------------------------------------------------------------
    "trade_balance": Concept(
        "Trade Balance",
        "Exports minus imports of goods and services; a deficit means buying more abroad.",
    ),
    "current_account": Concept(
        "Current Account Balance",
        "Trade plus income flows with the rest of the world; deficits need foreign funding.",
    ),
    "budget_balance": Concept(
        "Government Budget Balance",
        "Government revenue minus spending each month; negative is a deficit.",
    ),
    "government_debt_to_gdp": Concept(
        "Government Debt (% of GDP)",
        "Total government debt relative to the size of the economy.",
    ),
    # --- Energy (oil supply, demand and stocks) -----------------------------------------------
    "crude_oil_inventories": Concept(
        "Crude Oil Inventories",
        "Commercial crude oil in storage; builds tend to weigh on prices, draws support them.",
    ),
    "cushing_crude_stocks": Concept(
        "Cushing Crude Stocks",
        "Crude stored at Cushing, the WTI delivery hub; very low levels can squeeze prices.",
    ),
    "strategic_petroleum_reserve": Concept(
        "Strategic Petroleum Reserve",
        "Government emergency crude stocks; releases add supply to the market.",
    ),
    "crude_oil_production": Concept(
        "Crude Oil Production",
        "Barrels of crude oil produced per day.",
    ),
    "refinery_utilisation": Concept(
        "Refinery Utilisation",
        "Share of refining capacity in use: how much crude refiners are demanding.",
    ),
    "gasoline_inventories": Concept(
        "Gasoline Inventories",
        "Gasoline in storage; low stocks ahead of driving season support prices.",
    ),
    "diesel_inventories": Concept(
        "Diesel & Heating Oil Inventories",
        "Distillate fuel in storage, used by trucks, industry and heating.",
    ),
    "crude_oil_imports": Concept(
        "Crude Oil Imports",
        "Barrels of crude oil bought from abroad per day.",
    ),
    "crude_oil_exports": Concept(
        "Crude Oil Exports",
        "Barrels of crude oil sold abroad per day.",
    ),
    "total_fuel_demand": Concept(
        "Total Fuel Demand",
        "All petroleum products supplied to users per day: implied consumption.",
    ),
    "gasoline_demand": Concept(
        "Gasoline Demand",
        "Gasoline supplied to users per day: a read on driving demand.",
    ),
    "diesel_demand": Concept(
        "Diesel Demand",
        "Diesel and heating oil supplied per day: a read on freight and industry.",
    ),
    # --- Markets (reference prices) -------------------------------------------------------------
    "fx_eurusd": Concept("EUR/USD", "US dollars per euro."),
    "fx_gbpusd": Concept("GBP/USD", "US dollars per British pound."),
    "fx_usdjpy": Concept("USD/JPY", "Japanese yen per US dollar."),
    "fx_audusd": Concept("AUD/USD", "US dollars per Australian dollar."),
    "fx_nzdusd": Concept("NZD/USD", "US dollars per New Zealand dollar."),
    "fx_usdcad": Concept("USD/CAD", "Canadian dollars per US dollar."),
    "fx_usdchf": Concept("USD/CHF", "Swiss francs per US dollar."),
    "crude_oil_wti": Concept("WTI Crude Oil", "US benchmark crude price at Cushing, Oklahoma."),
    "crude_oil_brent": Concept("Brent Crude Oil", "International benchmark crude price."),
    "natural_gas": Concept("Natural Gas (Henry Hub)", "US benchmark natural gas price."),
}

# Series id -> concept, per country (US on FRED today; other countries add their own maps).
US_SERIES_CONCEPTS: dict[str, str] = {
    "AWHMAN": "factory_workweek",
    "ICSA": "initial_jobless_claims",
    "CCSA": "continuing_jobless_claims",
    "TEMPHELPS": "temporary_staffing_jobs",
    "JTSJOL": "job_openings",
    "JTSQUR": "quit_rate",
    "PAYEMS": "nonfarm_payrolls",
    "UNRATE": "unemployment_rate",
    "UEMPMEAN": "unemployment_duration",
    "ACOGNO": "consumer_goods_orders",
    "NEWORDER": "core_capital_goods_orders",
    "NOCDFSA066MSFRBPHI": "manufacturing_new_orders_survey",
    "PERMIT": "building_permits",
    "HOUST": "housing_starts",
    "HSN1F": "new_home_sales",
    "GDPC1": "real_gdp",
    "WEI": "weekly_economic_index",
    "INDPRO": "industrial_production",
    "RRSFS": "real_retail_sales",
    "PCEC96": "real_consumer_spending",
    "PI": "personal_income",
    "W875RX1": "real_income_excl_transfers",
    "CP": "corporate_profits",
    "ISRATIO": "inventories_to_sales",
    "CPIAUCSL": "consumer_prices",
    "CPILFESL": "core_consumer_prices",
    "CUSR0000SAS": "services_prices",
    "PCEPILFE": "core_pce_prices",
    "PPIFIS": "producer_prices",
    "ULCMFG": "unit_labour_costs",
    "T10YIE": "inflation_expectations_10y",
    "GASREGW": "gasoline_price",
    "FEDFUNDS": "policy_rate",
    "DGS2": "yield_2y",
    "DFII10": "real_yield_10y",
    "T10Y3M": "yield_curve_10y_3m",
    "T10YFF": "long_rate_vs_policy_rate",
    "WALCL": "central_bank_balance_sheet",
    "M2SL": "money_supply",
    "BUSLOANS": "business_loans",
    "TOTALSL": "consumer_credit",
    "UMCSENT": "consumer_sentiment",
    "NFCI": "financial_conditions",
    "STLFSI4": "financial_stress",
    "BAA10Y": "corporate_credit_spread",
    "DTWEXBGS": "trade_weighted_currency",
    "BOPGSTB": "trade_balance",
    "IEABC": "current_account",
    "MTSDS133FMS": "budget_balance",
    "GFDEGDQ188S": "government_debt_to_gdp",
    "WCESTUS1": "crude_oil_inventories",
    "W_EPC0_SAX_YCUOK_MBBL": "cushing_crude_stocks",
    "WCSSTUS1": "strategic_petroleum_reserve",
    "WCRFPUS2": "crude_oil_production",
    "WPULEUS3": "refinery_utilisation",
    "WGTSTUS1": "gasoline_inventories",
    "WDISTUS1": "diesel_inventories",
    "WCRIMUS2": "crude_oil_imports",
    "WCREXUS2": "crude_oil_exports",
    "WRPUPUS2": "total_fuel_demand",
    "WGFUPUS2": "gasoline_demand",
    "WDIUPUS2": "diesel_demand",
    "DEXUSEU": "fx_eurusd",
    "DEXUSUK": "fx_gbpusd",
    "DEXJPUS": "fx_usdjpy",
    "DEXUSAL": "fx_audusd",
    "DEXUSNZ": "fx_nzdusd",
    "DEXCAUS": "fx_usdcad",
    "DEXSZUS": "fx_usdchf",
    "DCOILWTICO": "crude_oil_wti",
    "DCOILBRENTEU": "crude_oil_brent",
    "DHHNGSP": "natural_gas",
}

# Euro area: the same concept keys as the US, so names match across countries (rule 18).
EA_SERIES_CONCEPTS: dict[str, str] = {
    "FM.D.U2.EUR.4F.KR.DFR.LEV": "policy_rate",
    "HICP.M.U2.N.000000.4D0.ANR": "consumer_prices",
    "HICP.M.U2.N.XEF000.4D0.ANR": "core_consumer_prices",
    "BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E": "money_supply",
}

SERIES_CONCEPTS: dict[tuple[str, str], str] = {
    ("US", series_id): concept for series_id, concept in US_SERIES_CONCEPTS.items()
} | {("EA", series_id): concept for series_id, concept in EA_SERIES_CONCEPTS.items()}

_EIA_REASON = "EIA Weekly Petroleum Status Report series are not on FRED (checked 4 Nov 2026)"

# US series from a source other than FRED, with the reason (rule 17: FRED first).
NON_FRED_ALLOWED: dict[str, str] = {
    series_id: _EIA_REASON
    for series_id in (
        "WCESTUS1",
        "W_EPC0_SAX_YCUOK_MBBL",
        "WCSSTUS1",
        "WCRFPUS2",
        "WPULEUS3",
        "WGTSTUS1",
        "WDISTUS1",
        "WCRIMUS2",
        "WCREXUS2",
        "WRPUPUS2",
        "WGFUPUS2",
        "WDIUPUS2",
    )
}

# Not stored because they are exactly derivable from series that are (no duplicated data).
REDUNDANT: dict[str, str] = {
    "DGS10": "10-year yield = real 10-year yield (DFII10) + 10-year breakeven (T10YIE)",
    "T10Y2Y": "10y minus 2y = (DFII10 + T10YIE) minus DGS2",
    "MPRIME": "Prime rate = fed funds + 3 points by banks' convention",
    "RSAFS": "Nominal retail sales = real retail sales (RRSFS) x CPI",
}


def concept_for(country: str, series_id: str) -> Concept | None:
    key = SERIES_CONCEPTS.get((country, series_id))
    return CONCEPTS[key] if key else None
