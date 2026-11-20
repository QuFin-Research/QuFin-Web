"""Coverage matrix: every taxonomy country against every indicator, generated from the database.

`uv run python -m app.cli coverage-matrix --out coverage_matrix.csv` replaces a hand-made seed
file. A seed file goes stale with every ingest, and one made from concept lists copies a concept's
sources and frequencies to every country, which is wrong for each cell. This one reads the stored
series, so each cell says what is really held: series, source, frequency, first and last period.

Each indicator has a scope, because a "gap" only means something where the indicator can exist
for the country:

- `global`: held, or declared in the catalog, for two or more countries. A country without it is
  a gap to close.
- `country_specific`: one country only (for example US jobless claims, JOLTS, the Empire State
  survey). Other countries are `NOT_APPLICABLE`; the owner is `HAVE`.
- `commodity`: the EIA's weekly US petroleum supply and demand series (stocks, production,
  refinery use, product supplied): a US market statistic, not a country one.
- `market`: a reference price (currency pairs, WTI, Brent, Henry Hub): a price, not a country
  statistic.

Each cell has one status:

- `HAVE`: stored, and the release check says it is usable.
- `OVERDUE`: stored, but its next release is late (or it needs review): not usable (rule 3).
- `NOT_LOADED`: in the catalog for the country, not stored yet.
- `GAP`: the indicator is global and the country has no series.
- `NOT_APPLICABLE`: the indicator is not global and the country is not its owner.

Coverage is `HAVE` over every cell of a global indicator (rule 34), not over the whole grid.
"""

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from app.data.country_sources import portal_label
from app.data.indicator_concepts import CONCEPTS, SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID
from app.data.taxonomy import COUNTRIES, pillar_for
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.stores.macro import MacroStore, SeriesSummary

Scope = Literal["global", "country_specific", "commodity", "market"]
Status = Literal["HAVE", "OVERDUE", "NOT_LOADED", "GAP", "NOT_APPLICABLE"]

GLOBAL_MIN_COUNTRIES = 2  # an indicator two countries share is a cross-country one
STATUSES: tuple[Status, ...] = ("HAVE", "OVERDUE", "NOT_LOADED", "GAP", "NOT_APPLICABLE")


@dataclass(frozen=True)
class Cell:
    concept_key: str
    indicator: str
    iso3: str
    country: str
    scope: Scope
    status: Status
    series_id: str
    source: str
    frequency: str
    first_period: str
    last_period: str
    pillar: str
    tier3_portal: str


def concept_scopes() -> dict[str, tuple[Scope, str | None]]:
    """Each declared concept's scope and, when it belongs to one country, that country's ISO2.

    From the catalog, not the database, so the scope does not change while a series is loading.
    """
    countries: dict[str, set[str]] = defaultdict(set)
    dimensions: dict[str, set[str]] = defaultdict(set)
    for (country, series_id), concept in SERIES_CONCEPTS.items():
        entry = BY_ID.get(series_id)
        if entry is None:
            continue
        countries[concept].add(country)
        dimensions[concept].add(entry.dimension)
    scopes: dict[str, tuple[Scope, str | None]] = {}
    for concept, held in countries.items():
        if len(held) >= GLOBAL_MIN_COUNTRIES:
            scopes[concept] = ("global", None)
        elif dimensions[concept] == {"energy"}:
            scopes[concept] = ("commodity", next(iter(held)))
        elif dimensions[concept] == {"markets"}:
            scopes[concept] = ("market", next(iter(held)))
        else:
            scopes[concept] = ("country_specific", next(iter(held)))
    return scopes


def build(session: Session, today: date | None = None) -> list[Cell]:
    """One cell per taxonomy country and declared indicator."""
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    releases = store.first_releases(today - LAG_WINDOW)
    stored: dict[tuple[str, str], SeriesSummary] = {}
    for s in store.list_series():
        concept = SERIES_CONCEPTS.get((s.meta.country, s.meta.id))
        if concept and s.meta.id in BY_ID:
            # One series per country and concept (rule 16); the first is shown if that ever fails.
            stored.setdefault((concept, s.meta.country), s)
    declared: dict[tuple[str, str], str] = {}
    for (country, series_id), concept in SERIES_CONCEPTS.items():
        if series_id in BY_ID:
            declared.setdefault((concept, country), series_id)
    scopes = concept_scopes()
    pillars: dict[str, str] = {}
    for (country, series_id), concept in SERIES_CONCEPTS.items():
        if series_id in BY_ID and concept not in pillars:
            pillars[concept] = pillar_for(country, series_id) or ""
    cells = []
    for concept in sorted(scopes):
        scope = scopes[concept][0]
        name = CONCEPTS[concept].name if concept in CONCEPTS else concept
        for place in COUNTRIES:
            key = (concept, place.iso2)
            series = stored.get(key)
            series_id = source = frequency = first = last = ""
            if series is not None:
                meta = series.meta
                series_id, source, frequency = meta.id, meta.source, meta.frequency
                first = series.first_period.isoformat() if series.first_period else ""
                last = series.last_period.isoformat() if series.last_period else ""
                fresh = macro_status(
                    meta, series.last_period, releases.get(meta.id, {}), today
                ).freshness
                status: Status = "HAVE" if fresh.usable else "OVERDUE"
            elif key in declared:
                series_id, status = declared[key], "NOT_LOADED"
                source = BY_ID[series_id].source
            else:
                # Only a global indicator can be missing: a country-specific one is held by its
                # owner (declared, so handled above) and cannot exist for the others.
                status = "GAP" if scope == "global" else "NOT_APPLICABLE"
            pillar = pillar_for(place.iso2, series_id) if series_id else None
            cells.append(
                Cell(
                    concept,
                    name,
                    place.iso3,
                    place.name,
                    scope,
                    status,
                    series_id,
                    source,
                    frequency,
                    first,
                    last,
                    pillar or pillars.get(concept, ""),
                    portal_label(place.iso3) if status in ("GAP", "NOT_LOADED", "OVERDUE") else "",
                )
            )
    return cells


def write_csv(cells: list[Cell], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(Cell)])
        writer.writeheader()
        for cell in cells:
            writer.writerow(asdict(cell))


@dataclass(frozen=True)
class Summary:
    cells: int
    by_status: dict[str, int]
    applicable: int  # every cell of a global indicator
    have: int  # HAVE cells of global indicators
    concepts: dict[str, tuple[int, int, int]]  # global concept -> (have, not usable or loaded, gap)
    scopes: dict[str, int]


def summarize(cells: list[Cell]) -> Summary:
    by_status: dict[str, int] = {s: 0 for s in STATUSES}
    scopes: dict[str, set[str]] = defaultdict(set)
    concepts: dict[str, list[int]] = {}
    for c in cells:
        by_status[c.status] += 1
        scopes[c.scope].add(c.concept_key)
        if c.scope == "global":
            have, other, gap = concepts.setdefault(c.concept_key, [0, 0, 0])
            if c.status == "HAVE":
                have += 1
            elif c.status == "GAP":
                gap += 1
            else:
                other += 1
            concepts[c.concept_key] = [have, other, gap]
    applicable = sum(sum(v) for v in concepts.values())
    return Summary(
        cells=len(cells),
        by_status=by_status,
        applicable=applicable,
        have=sum(v[0] for v in concepts.values()),
        concepts={k: (v[0], v[1], v[2]) for k, v in concepts.items()},
        scopes={k: len(v) for k, v in scopes.items()},
    )


def country_gaps(cells: list[Cell]) -> list[tuple[str, str, int, int, int]]:
    """Per country, over the global indicators only: (iso3, name, have, unusable, gap)."""
    rows: dict[str, list[int]] = {}
    names: dict[str, str] = {}
    for c in cells:
        names[c.iso3] = c.country
        counts = rows.setdefault(c.iso3, [0, 0, 0])
        if c.scope != "global":
            continue
        if c.status == "HAVE":
            counts[0] += 1
        elif c.status == "GAP":
            counts[2] += 1
        else:
            counts[1] += 1
    return [(iso3, names[iso3], v[0], v[1], v[2]) for iso3, v in rows.items()]


def format_summary(summary: Summary, top: int = 12) -> str:
    countries = summary.cells // max(1, sum(summary.scopes.values()))
    lines = [
        f"coverage matrix: {summary.cells} cells, {countries} countries, "
        f"{sum(summary.scopes.values())} indicators",
        "  indicators by scope: "
        + ", ".join(f"{k} {v}" for k, v in sorted(summary.scopes.items())),
        "  cells by status:     " + ", ".join(f"{k} {v}" for k, v in summary.by_status.items()),
    ]
    pct = summary.have / summary.applicable if summary.applicable else 0.0
    lines.append(
        f"  coverage of global indicators: {summary.have} of {summary.applicable} cells ({pct:.0%})"
    )
    worst = sorted(summary.concepts.items(), key=lambda kv: (-kv[1][2], kv[0]))[:top]
    lines.append(f"  largest gaps (of {len(summary.concepts)} global indicators):")
    lines.append(f"    {'indicator':<38}{'have':>6}{'unusable':>10}{'gap':>6}")
    for concept, (have, other, gap) in worst:
        lines.append(f"    {concept:<38}{have:>6}{other:>10}{gap:>6}")
    return "\n".join(lines)
