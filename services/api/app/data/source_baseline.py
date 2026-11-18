"""Source decisions every database must hold (rules 16, P).

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

from app.data.gap_ids import HICP_GEO
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
_ISO3 = {iso2: iso3 for iso3, iso2 in ISO3_TO_ISO2.items()}


def _predecessor(iso2: str) -> tuple[str, str, date] | None:
    """The series that served consumer prices before Eurostat: id, source, and from when."""
    if iso2 == "PT":
        return "CP0000PTM086NEST", "fred", date(2026, 11, 18)
    if iso2 in ("MT", "RS"):
        return f"BIS_CPI_{iso2}", "bis", FIRST_DATE
    if iso2 in _LAST_BEFORE:
        return f"IMF_CPI_{_ISO3[iso2]}", "imf", FIRST_DATE
    return None  # Kosovo: no series before


def _decision(iso2: str, geo: str) -> BaselineDecision:
    before = _predecessor(iso2)
    if before is None:
        reason = (
            "New pair: Eurostat is the only source that publishes Kosovo's HICP (October 2026 at "
            "the 19 Nov 2026 probe). Provisional until a release cycle is measured (rule P)."
        )
        return BaselineDecision(
            iso2, CONCEPT, f"ESTAT_HICP_{geo}", "eurostat", SWITCH_DATE, "provisional", reason
        )
    old_id, old_source, old_from = before
    reason = (
        f"Eurostat held October 2026 at the 19 Nov 2026 probe (dataset updated 18 Nov); {old_id} "
        f"({old_source}) stopped at {_LAST_BEFORE[iso2]}. Provisional until a release cycle is "
        "measured (rule P). Eurostat's series starts later than the one it replaces; the earlier "
        "history stays in the retired series."
    )
    return BaselineDecision(
        iso2,
        CONCEPT,
        f"ESTAT_HICP_{geo}",
        "eurostat",
        SWITCH_DATE,
        "provisional",
        reason,
        Predecessor(
            old_id,
            old_source,
            old_from,
            "Served the pair before the switch to Eurostat (rule P, 19 Nov 2026).",
        ),
    )


BASELINE: tuple[BaselineDecision, ...] = tuple(_decision(i, g) for i, g in HICP_GEO.items())

# Series kept although they are no longer in the catalog: the pair's history stays readable as of
# dates before the switch (rule 16). The doctor and the pruning never delete them.
PREDECESSORS: frozenset[str] = frozenset(
    b.predecessor.series_id for b in BASELINE if b.predecessor is not None
)
