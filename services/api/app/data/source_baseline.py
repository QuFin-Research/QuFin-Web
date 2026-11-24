"""Source decisions every database must hold (rules 16, 38).

`uv run python -m app.cli source-decision --baseline` applies them. A pair already served by the
series named here is left alone, so running it twice changes nothing. When a pair has no decision
yet, its predecessor (the series that served it before) is recorded first, so it is retired and kept
for as-of reads before the change instead of being deleted.

Decisions made later are recorded with `source-decision` at the time; add one here only when every
database, including a fresh one, must hold it. Apply them first, then load the new series
(`ingest-eurostat`): a retired series gives up its canonical code (one live series per country and
indicator), which the new series takes.
"""

from dataclasses import dataclass
from datetime import date

from app.data.bis_ids import BATCH_A, BIS_COUNTRY
from app.data.gap_ids import (
    BATCH_B_CORE,
    BATCH_B_IP,
    BATCH_C_CA,
    BATCH_C_GDP,
    BATCH_E_TRADE,
    HICP_GEO,
    OECD_FLOW_SERIES,
)
from app.data.indicator_concepts import _OECD_CONCEPT, BIS_CONCEPT
from app.data.macro_catalog import _OECD_BATCH_B, _OECD_ID, _OECD_ISO2
from app.data.macro_ids import ISO3_TO_ISO2

CONCEPT = "consumer_prices"
SWITCH_DATE = date(2026, 11, 19)
FIRST_DATE = date(1990, 1, 1)


@dataclass(frozen=True)
class Predecessor:
    series_id: str
    source: str
    effective_from: date
    reason: str


@dataclass(frozen=True)
class BaselineDecision:
    country: str
    concept: str
    series_id: str
    source: str
    effective_from: date
    status: str
    reason: str
    predecessor: Predecessor | None = None


# The month the series serving each pair stopped at, at the 19 Nov 2026 probe. Eurostat had
# October 2026 for all of them (dataset updated 18 Nov 2026, 11:00 CET).
_LAST_BEFORE: dict[str, str] = {
    "AT": "2026-09", "BG": "2026-09", "CY": "2026-09", "CZ": "2026-09", "DE": "2026-09",
    "DK": "2026-09", "ES": "2026-09", "FI": "2026-09", "FR": "2026-09", "GR": "2026-09",
    "HR": "2026-09", "HU": "2026-09", "IE": "2026-09", "IS": "2026-08", "IT": "2026-09",
    "LT": "2026-09", "LV": "2026-09", "ME": "2026-09", "MK": "2026-08", "MT": "2026-08",
    "NL": "2026-09", "NO": "2026-09", "PL": "2026-09", "PT": "2026-09", "RO": "2026-08",
    "RS": "2026-09", "SE": "2026-09", "SK": "2026-09", "TR": "2026-09",
}  # fmt: skip
# Level with Eurostat at the probe: the IMF had October too. The tie goes to the more native
# source, Eurostat (rule 38, Part 0).
_TIED: frozenset[str] = frozenset({"AL", "BE", "CH", "EE", "LU", "SI"})
_ISO3 = {iso2: iso3 for iso3, iso2 in ISO3_TO_ISO2.items()}


def _predecessor(iso2: str) -> tuple[str, str, date] | None:
    """The series that served consumer prices before Eurostat: id, source, and from when."""
    if iso2 == "PT":
        return "CP0000PTM086NEST", "fred", date(2026, 11, 18)
    if iso2 in ("MT", "RS"):
        return f"BIS_CPI_{iso2}", "bis", FIRST_DATE
    if iso2 in _LAST_BEFORE or iso2 in _TIED:
        return f"IMF_CPI_{_ISO3[iso2]}", "imf", FIRST_DATE
    return None  # Kosovo: no series before


def _decision(iso2: str, geo: str) -> BaselineDecision:
    before = _predecessor(iso2)
    if before is None:
        reason = (
            "Eurostat serves the pair (rule 38, Bloc aggregator first): it is the only source that "
            "publishes Kosovo's HICP (October 2026 at the 19 Nov 2026 probe)."
        )
        return BaselineDecision(
            iso2, CONCEPT, f"ESTAT_HICP_{geo}", "eurostat", SWITCH_DATE, "confirmed", reason
        )
    old_id, old_source, old_from = before
    probe = (
        f"{old_id} ({old_source}) also held October 2026"
        if iso2 in _TIED
        else f"{old_id} ({old_source}) stopped at {_LAST_BEFORE[iso2]}"
    )
    reason = (
        "Eurostat serves the pair (rule 38, Bloc aggregator first): one definition for the bloc, "
        "whatever any other source's timing. First moved on 19 Nov 2026, when Eurostat held "
        f"October 2026 (dataset updated 18 Nov) and {probe}; provisional until v3.5 made it final. "
        "Eurostat's series may start later than the one it replaces; the earlier history stays "
        "in the retired series."
    )
    return BaselineDecision(
        iso2,
        CONCEPT,
        f"ESTAT_HICP_{geo}",
        "eurostat",
        SWITCH_DATE,
        "confirmed",
        reason,
        Predecessor(
            old_id,
            old_source,
            old_from,
            "Served the pair before the switch to Eurostat (rule 38, 19 Nov 2026).",
        ),
    )


# The United States' commercial property prices: a new pair, decided on 19 Nov 2026 (rule 38).
_US_COMMERCIAL_PROPERTY = BaselineDecision(
    "US",
    "commercial_property_prices",
    "BIS_CPP_US",
    "bis",
    SWITCH_DATE,
    "provisional",
    "BIS index (CoStar repeat sales since 1996, Federal Reserve Financial Accounts source) held "
    "Q2 2026 on 19 Nov 2026; FRED's COMREPUSQ159N (the IMF's financial soundness indicator, "
    "annual change) stopped at Q1 2026 and reached FRED in batches, the latest on 1 Oct 2026. "
    "The BIS is earlier at the same frequency. Provisional until a release cycle is measured "
    "(rule 38).",
)

BATCH_A_DATE = date(2026, 11, 22)
BATCH_E_DATE = date(2026, 11, 25)


def _batch_a(code: str, area: str) -> BaselineDecision:
    return BaselineDecision(
        BIS_COUNTRY.get(area, area),
        BIS_CONCEPT[code],
        f"BIS_{code}_{area}",
        "bis",
        BATCH_A_DATE,
        "provisional",
        "A new pair: the BIS is the only candidate with a current feed (probe of 21 Nov 2026; "
        "latest period 2026-01 to 2026-10), so it serves from the start. Provisional until a "
        "release cycle is measured (rule 38).",
    )


def _batch_b_eurostat(concept: str, series_id: str, country: str, month: str) -> BaselineDecision:
    return BaselineDecision(
        country,
        concept,
        series_id,
        "eurostat",
        BATCH_A_DATE,
        "confirmed",
        f"Bloc aggregator first (rule 38): Eurostat serves the pair whenever it publishes it; "
        f"its latest month was {month} on 22 Nov 2026.",
    )


def _batch_b_oecd(concept: str, series_id: str, country: str) -> BaselineDecision:
    return BaselineDecision(
        country,
        concept,
        series_id,
        "oecd",
        BATCH_A_DATE,
        "provisional",
        "A new pair: the OECD is the only candidate with a current feed (probe of 21 Nov 2026; "
        "latest month 2026-09 or 2026-10), so it serves from the start. Provisional until a "
        "release cycle is measured (rule 38).",
    )


def _batch_c_eurostat(concept: str, series_id: str, country: str, quarter: str) -> BaselineDecision:
    return BaselineDecision(
        country,
        concept,
        series_id,
        "eurostat",
        BATCH_A_DATE,
        "confirmed",
        f"Bloc aggregator first (rule 38): Eurostat serves the pair whenever it publishes it; "
        f"its latest quarter was {quarter} on 22 Nov 2026.",
    )


def _batch_e_eurostat_trade(geo: str, country: str) -> BaselineDecision:
    return BaselineDecision(
        country,
        "merchandise_trade_balance",
        f"ESTAT_TRADE_{geo}",
        "eurostat",
        BATCH_E_DATE,
        "confirmed",
        "Bloc aggregator first (rule 38): Eurostat is the priority source for this EU pair. "
        "The owner accepted commercial reuse with attribution on 25 Nov 2026; serving remains "
        "subject to the reviewed eligibility PR.",
    )


def _batch_d_oecd(concept: str, series_id: str, country: str) -> BaselineDecision:
    return BaselineDecision(
        country,
        concept,
        series_id,
        "oecd",
        BATCH_A_DATE,
        "provisional",
        "A new pair: the OECD is the only candidate with a current feed (probe of 21 Nov 2026), "
        "so it serves from the start. Provisional until a release cycle is measured (rule 38).",
    )


BASELINE: tuple[BaselineDecision, ...] = (
    *(_decision(i, g) for i, g in HICP_GEO.items()),
    _US_COMMERCIAL_PROPERTY,
    *(_batch_a(code, area) for code, areas in BATCH_A.items() for area in areas),
    *(
        _batch_b_eurostat("core_consumer_prices", f"ESTAT_CORE_{g}", i, "2026-10")
        for g, i in BATCH_B_CORE.items()
    ),
    *(
        _batch_b_eurostat("industrial_production", f"ESTAT_IP_{g}", i, "2026-09")
        for g, i in BATCH_B_IP.items()
    ),
    *(
        _batch_b_oecd(_OECD_CONCEPT[m], f"OECD_{_OECD_ID[m]}_{a}", _OECD_ISO2[a])
        for m, areas in _OECD_BATCH_B.items()
        for a in areas
    ),
    *(_batch_c_eurostat("real_gdp", f"ESTAT_GDP_{g}", g, "2026-Q2") for g in BATCH_C_GDP),
    *(
        _batch_c_eurostat("current_account_to_gdp", f"ESTAT_CA_{g}", g, "2026-Q2")
        for g in BATCH_C_CA
    ),
    *(_batch_e_eurostat_trade(geo, country) for geo, country in BATCH_E_TRADE.items()),
    *(_batch_d_oecd(s.concept, s.id, s.country) for s in OECD_FLOW_SERIES),
)

# Series kept although they are no longer in the catalog: the pair's history stays readable as of
# dates before the switch (rule 16). The doctor and the pruning never delete them.
PREDECESSORS: frozenset[str] = frozenset(
    b.predecessor.series_id for b in BASELINE if b.predecessor is not None
)
