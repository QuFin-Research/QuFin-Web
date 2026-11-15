"""Ingest Eurostat series (industrial production, core HICP) into the point-in-time macro store.

Eurostat gives current values with no vintages, so each period is dated by its usual release lag
(`app/data/eurostat_calendar.py`), erring late.
"""

import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.eurostat import EurostatClient, EurostatError
from app.data.eurostat_calendar import release_of
from app.data.gap_ids import EUROSTAT_BY_ID
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, start_for
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "Eurostat (from national statistical institutes)"
PAUSE_SECONDS = 2.0


def ingest(
    client: EurostatClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """Each series in its own request and transaction; one failure does not stop the rest."""
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results: list[IngestResult] = []
    for i, series_id in enumerate(series_ids):
        spec = EUROSTAT_BY_ID.get(series_id)
        entry = BY_ID.get(series_id)
        if spec is None or entry is None or entry.source != "eurostat":
            results.append(IngestResult(series_id, None, "not a Eurostat series in the catalog"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        try:
            fetched = client.series(spec.dataset, spec.filters, start_for(series_id, start))
            meta = SeriesMeta(
                id=series_id,
                source="eurostat",
                title=spec.title,
                units=spec.units,
                frequency="Monthly",
                seasonal_adjustment=spec.adjustment,
                country=entry.country,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=PUBLISHER,
                release_name=spec.release,
            )
            rows = store.record_latest(meta, fetched.observations, release_of(spec.dataset), today)
        except EurostatError as exc:
            session.rollback()
            log.warning("Eurostat ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        log.info("Ingested %s: %d new or revised months", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
