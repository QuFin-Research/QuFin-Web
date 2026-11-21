"""What the discovery job asks each source (rule 34): one probe per source and indicator.

A probe says where an indicator would be found and how to ask for every economy at once (OECD:
one wildcard request) or one economy at a time (Eurostat: one series per request). The keys were
checked live on 21 Nov 2026. Probes read, they never store: the report says what each source
publishes, and a reviewed pull request decides what is staged or served (rules 26, 34 and 38).
Eurostat comes first for the economies it serves (rule 38, *Bloc aggregator first*).
"""

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["oecd", "eurostat"]


@dataclass(frozen=True)
class Probe:
    concept: str
    source: Kind
    note: str
    # OECD: the dataflow and a key with the area left open.
    flow: str = ""
    key: str = ""
    # Eurostat: the dataset and the filters (the economy is added to them).
    dataset: str = ""
    filters: dict[str, str] = field(default_factory=dict)


OECD_STES = "OECD.SDD.STES,DSD_STES@"
OECD_PRICES = "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,"

PROBES: tuple[Probe, ...] = (
    Probe(
        "industrial_production",
        "eurostat",
        "Production in industry, seasonally and calendar adjusted, 2021=100",
        dataset="sts_inpr_m",
        filters={"freq": "M", "indic_bt": "PRD", "nace_r2": "B-D", "s_adj": "SCA", "unit": "I21"},
    ),
    Probe(
        "industrial_production",
        "oecd",
        "Production volume, industry excluding construction, seasonally adjusted",
        flow=f"{OECD_STES}DF_INDSERV,",
        key=".M.PRVM.IX.BTE.Y._Z._Z.N",
    ),
    Probe(
        "core_consumer_prices",
        "eurostat",
        "HICP excluding energy, food, alcohol and tobacco, annual rate",
        dataset="prc_hicp_minr",
        filters={"freq": "M", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD"},
    ),
    Probe(
        "core_consumer_prices",
        "oecd",
        "CPI excluding food and energy, index",
        flow=OECD_PRICES,
        key=".M.N.CPI.IX._TXCP01_NRG.N._Z",
    ),
    Probe(
        "money_supply",
        "oecd",
        "Broad money, national currency, seasonally adjusted",
        flow=f"{OECD_STES}DF_MONAGG,",
        key=".M.MABM.XDC._Z.Y._Z._Z.N",
    ),
)
