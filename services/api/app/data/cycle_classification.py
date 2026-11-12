"""Business-cycle timing for series that are not Conference Board index components.

Every catalog series has a cycle: leading (turns before the economy), coincident (moves with it)
or lagging (confirms after). The Conference Board classifies its own index components; they are
tagged in app/data/macro_catalog.py. Everything else is QuFin's classification from standard
analyst practice, with the reason below. It is judgement, not a published standard: a series
may be argued either way, so change it here (one place) with the reason, never silently.
A series without a cycle fails to load (macro_catalog.py), so a new series cannot skip this.
"""

from typing import Literal

from app.data.bis_ids import BIS_SERIES, MEASURES
from app.data.gap_ids import FRED_ADDITIONS, ONS_SERIES
from app.data.macro_ids import IMF_CPI, OECD_MACRO
from app.data.reserves_ids import RESERVES

Cycle = Literal["leading", "coincident", "lagging"]

_MARKET = "Market prices discount the future, so they turn before activity."
_COMMODITY = "Commodity prices respond to expected demand and turn before activity."
_FISCAL = "Fiscal balances and debt follow the cycle (automatic stabilisers)."
_INVENTORY = "Inventories build or draw after demand has already changed."
_FLOW = "Trade flows reflect current demand and prices."
_PRODUCT = "Product supplied is consumption: it moves with activity."
_INFLATION = "Inflation follows the cycle; it confirms rather than predicts."

QUFIN_CYCLE: dict[str, tuple[Cycle, str]] = {
    # --- Prices -----------------------------------------------------------------------------
    "PCEPILFE": ("lagging", _INFLATION),
    "PPIFIS": ("coincident", "Producer prices move with industrial activity and input costs."),
    "GASREGW": ("coincident", "Retail fuel prices move with crude oil and current demand."),
    "HICP.M.U2.N.000000.4D0.ANR": ("lagging", _INFLATION),
    "HICP.M.U2.N.XEF000.4D0.ANR": ("lagging", _INFLATION),
    "T10YIE": ("leading", "Market inflation expectations move before realised inflation."),
    # --- Rates, credit and money --------------------------------------------------------------
    "DGS2": ("leading", "The 2-year yield prices the expected policy path ahead of the data."),
    "DFII10": ("leading", "Real yields move first on growth and policy expectations."),
    "BAA10Y": ("leading", "Credit spreads widen before downturns."),
    "FEDFUNDS": ("lagging", "Central banks set rates in response to the economy."),
    "FM.D.U2.EUR.4F.KR.DFR.LEV": ("lagging", "Central banks set rates in response to the economy."),
    "WALCL": ("lagging", "The central bank changes its balance sheet in response to conditions."),
    "M2SL": ("leading", "Money growth tends to lead activity."),
    "BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E": ("leading", "Money growth tends to lead activity."),
    "CP": ("leading", "Corporate profits turn down before recessions."),
    # --- Currencies ---------------------------------------------------------------------------
    "DEXUSEU": ("leading", _MARKET),
    "DEXUSUK": ("leading", _MARKET),
    "DEXJPUS": ("leading", _MARKET),
    "DEXUSAL": ("leading", _MARKET),
    "DEXUSNZ": ("leading", _MARKET),
    "DEXCAUS": ("leading", _MARKET),
    "DEXSZUS": ("leading", _MARKET),
    "DTWEXBGS": ("leading", _MARKET),
    # --- Commodity prices ---------------------------------------------------------------------
    "DCOILWTICO": ("leading", _COMMODITY),
    "DCOILBRENTEU": ("leading", _COMMODITY),
    "DHHNGSP": ("leading", _COMMODITY),
    # --- External and fiscal ------------------------------------------------------------------
    "BOPGSTB": ("lagging", "Trade balances adjust after the cycle has turned."),
    **{
        series_id: (
            "coincident",
            "Reserves move with current balance-of-payments flows and central bank intervention.",
        )
        for series_id in RESERVES
    },
    "IEABC": ("lagging", "The current account adjusts after the cycle has turned."),
    "MTSDS133FMS": ("lagging", _FISCAL),
    "GFDEGDQ188S": ("lagging", _FISCAL),
    "TREAS_DEBT_TOTAL": ("lagging", _FISCAL),
    "TREAS_AVG_RATE_MARKETABLE": ("lagging", _FISCAL),
    "TREAS_INTEREST_EXPENSE": ("lagging", _FISCAL),
    # --- Energy (EIA weekly petroleum) ----------------------------------------------------------
    "WCESTUS1": ("lagging", _INVENTORY),
    "W_EPC0_SAX_YCUOK_MBBL": ("lagging", _INVENTORY),
    "WGTSTUS1": ("lagging", _INVENTORY),
    "WDISTUS1": ("lagging", _INVENTORY),
    "WCSSTUS1": ("lagging", "Government reserve stocks change by policy decision, after events."),
    "WCRFPUS2": ("lagging", "Production responds to prices with a lag."),
    "WPULEUS3": ("coincident", "Refinery runs track current demand for fuel."),
    "WCRIMUS2": ("coincident", _FLOW),
    "WCREXUS2": ("coincident", _FLOW),
    "WRPUPUS2": ("coincident", _PRODUCT),
    "WGFUPUS2": ("coincident", _PRODUCT),
    "WDIUPUS2": ("coincident", _PRODUCT),
    # --- BLS (P1-12) ----------------------------------------------------------------------------
    "ECIALLCIV": ("lagging", "Wages and benefits follow price inflation with a lag."),
    # --- BIS (P1-22) --------------------------------------------------------------------------
    **{
        series_id: (MEASURES[code].cycle, MEASURES[code].cycle_reason)
        for series_id, (code, _area) in BIS_SERIES.items()
    },
    # --- Coverage gaps (Sprints 1-4) ---------------------------------------------------------
    **{a.id: (a.cycle, a.cycle_reason) for a in FRED_ADDITIONS},
    **{s.id: (s.cycle, s.cycle_reason) for s in ONS_SERIES},
    # --- Consumer prices and unemployment by country (P1-23) ---------------------------------
    **{series_id: ("lagging", _INFLATION) for series_id in IMF_CPI},
    **{
        series_id: ("lagging", "Employers hire and fire after output has already turned.")
        for series_id in OECD_MACRO
    },
}
