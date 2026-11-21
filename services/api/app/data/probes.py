"""What the discovery job asks each source (rule 34): one probe per source and indicator.

A probe says where an indicator would be found and how to ask for every economy at once (OECD:
one wildcard request) or one economy at a time (Eurostat: one series per request). The keys were
checked live on 21 Nov 2026. Probes read, they never store: the report says what each source
publishes, and a reviewed pull request decides what is staged or served (rules 26, 34 and 38).
Eurostat comes first for the economies it serves (rule 38, *Bloc aggregator first*).
"""

from dataclasses import dataclass, field
from typing import Literal

from app.data.bis_ids import MEASURES
from app.data.indicator_concepts import BIS_CONCEPT

Kind = Literal["oecd", "eurostat", "bis"]


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
    # BIS: the dataflow is `flow`, the key has the economy left open, and these two say which
    # dimension names the economy and which version of the dataflow to ask.
    area_dimension: str = "REF_AREA"
    version: str = "1.0"
    months: int = 0  # a longer window than the default, for a quarterly indicator


OECD_STES = "OECD.SDD.STES,DSD_STES@"
OECD_PRICES = "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,"

OECD_CLI = "OECD.SDD.STES,DSD_STES@DF_CLI,"
_BIS_QUARTERLY_MONTHS = 18  # the latest quarter can sit more than 8 months back

# One wildcard request per BIS measure: the economy position of the key is left empty. The
# commercial property measure has a template of its own (`{part}`) and no wildcard, so it is not
# probed yet.
_BIS_PROBES = tuple(
    Probe(
        BIS_CONCEPT[m.code],
        "bis",
        m.title,
        flow=m.flow,
        key=m.key.replace("{areas}", ""),
        area_dimension=m.area_dimension,
        version=m.version,
        months=_BIS_QUARTERLY_MONTHS if m.frequency == "Quarterly" else 0,
    )
    for m in MEASURES.values()
    if "{areas}" in m.key and "{part}" not in m.key and m.code in BIS_CONCEPT
)

PROBES: tuple[Probe, ...] = (
    *_BIS_PROBES,
    Probe(
        "leading_index",
        "oecd",
        "Composite leading indicator, amplitude adjusted",
        flow=OECD_CLI,
        key=".M.LI.IX..AA.IX..H",
    ),
    Probe(
        "business_confidence",
        "oecd",
        "Business confidence indicator, amplitude adjusted",
        flow=OECD_CLI,
        key=".M.BCICP.IX..AA.IX..H",
    ),
    Probe(
        "consumer_sentiment",
        "oecd",
        "Consumer confidence indicator, amplitude adjusted",
        flow=OECD_CLI,
        key=".M.CCICP.IX..AA.IX..H",
    ),
    Probe(
        "unemployment_rate",
        "oecd",
        "Unemployment rate, 15 years and over, monthly",
        flow="OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,",
        key=".UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M",
    ),
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
