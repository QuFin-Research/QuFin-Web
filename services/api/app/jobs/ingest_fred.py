"""Ingest FRED/ALFRED series (metadata and full vintage history) into the macro store."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.connectors.fred import FredClient, FredError
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, CatalogSeries
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    series_id: str
    rows: int | None
    error: str | None = None


def ingest_series(
    client: FredClient,
    store: MacroStore,
    entry: CatalogSeries,
    observation_start: date = DEFAULT_OBSERVATION_START,
) -> int:
    info = client.series(entry.id)
    vintages = client.vintages(entry.id, observation_start)
    meta = SeriesMeta(
        id=info.id,
        source=entry.source,
        title=info.title,
        units=info.units,
        frequency=info.frequency,
        seasonal_adjustment=info.seasonal_adjustment,
        country=entry.country,
        dimension=entry.dimension,
        last_updated=info.last_updated,
    )
    return store.replace_series(meta, vintages)


def ingest(
    client: FredClient,
    session: Session,
    series_ids: Iterable[str],
    observation_start: date = DEFAULT_OBSERVATION_START,
) -> list[IngestResult]:
    """Ingests each series in its own transaction; one failure does not stop the rest."""
    store = MacroStore(session)
    results = []
    for series_id in series_ids:
        entry = BY_ID.get(series_id)
        if entry is None:
            results.append(IngestResult(series_id, None, "not in the macro catalog"))
            continue
        try:
            rows = ingest_series(client, store, entry, observation_start)
        except FredError as exc:
            session.rollback()
            log.warning("FRED ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        log.info("Ingested %s: %d vintage rows", series_id, rows)
        results.append(IngestResult(series_id, rows))
    return results
