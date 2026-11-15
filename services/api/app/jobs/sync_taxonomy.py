"""Keep the country dimension and every series' canonical code in step with the taxonomy.

The taxonomy (`app/data/taxonomy.py`) is the single source of truth; the database holds a copy so
queries can join on it. Run after a catalog or taxonomy change, or on any database restored from
before the taxonomy existed. Every ingest also sets a series' code when it stores its metadata.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.data.taxonomy import (
    COUNTRIES,
    TaxonomyError,
    canonical_code,
    pillar_for,
    scale_of,
)
from app.stores.macro import MacroSeriesRow
from app.stores.taxonomy import CountryRow


@dataclass(frozen=True)
class SyncResult:
    countries: int
    series: int
    changed: int
    uncoded: tuple[str, ...] = ()  # catalog series whose code could not be built


def sync(session: Session) -> SyncResult:
    for c in COUNTRIES:
        place = session.get(CountryRow, c.iso3) or CountryRow(iso3=c.iso3)
        place.iso2, place.name, place.currency, place.central_bank = (
            c.iso2,
            c.name,
            c.currency,
            c.central_bank,
        )
        place.g7, place.g20, place.gcc, place.em = c.g7, c.g20, c.gcc, c.em
        session.add(place)

    rows = list(session.scalars(select(MacroSeriesRow)))
    seen: dict[str, str] = {}
    wanted: dict[str, tuple[str | None, str | None, float]] = {}
    uncoded: list[str] = []
    for row in rows:
        try:
            code = canonical_code(row.id, row.country, row.frequency, row.seasonal_adjustment)
        except TaxonomyError:
            code = None
        if code is None and (row.country, row.id) in SERIES_CONCEPTS:
            uncoded.append(row.id)
        if code is not None:
            # Two series with one code carry the same thing: a duplicate indicator (rule 16).
            if code in seen:
                raise TaxonomyError(f"{code} belongs to both {seen[code]} and {row.id}")
            seen[code] = row.id
        wanted[row.id] = (code, pillar_for(row.country, row.id), scale_of(row.units))

    changed = 0
    for row in rows:
        code, pillar, scale = wanted[row.id]
        if (row.canonical_code, row.pillar, row.scale) != (code, pillar, scale):
            row.canonical_code, row.pillar, row.scale = code, pillar, scale
            changed += 1
    session.commit()
    return SyncResult(len(COUNTRIES), len(rows), changed, tuple(uncoded))
