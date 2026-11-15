"""Ingest UK ONS series (unemployment, real GDP, core CPI) into the point-in-time macro store.

The ONS gives current values with no vintages, so each period is dated by its usual release lag.
"""

import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.ons import OnsClient, OnsError
from app.data.gap_ids import ONS_BY_ID
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, start_for
from app.data.ons_calendar import release_for
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "Office for National Statistics (UK)"
RELEASES = {
    "MGSX": "ONS Labour market overview",
    "ABMI": "ONS GDP quarterly national accounts",
    "DKO8": "ONS Consumer price inflation",
    "BOKI": "ONS UK trade",
}
PAUSE_SECONDS = 2.0


def ingest(
    client: OnsClient,
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
        spec = ONS_BY_ID.get(series_id)
        entry = BY_ID.get(series_id)
        if spec is None or entry is None or entry.source != "ons":
            results.append(IngestResult(series_id, None, "not an ONS series in the catalog"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        try:
            fetched = client.series(spec.path, spec.frequency, start_for(series_id, start))
            meta = SeriesMeta(
                id=series_id,
                source="ons",
                title=spec.title,
                units=spec.units,
                frequency=spec.frequency,
                seasonal_adjustment="Seasonally Adjusted",
                country=entry.country,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=PUBLISHER,
                release_name=RELEASES[spec.cdid],
            )
            release = release_for(spec.frequency, spec.cdid)
            rows = store.record_latest(meta, fetched.observations, release, today)
        except OnsError as exc:
            session.rollback()
            log.warning("ONS ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        log.info("Ingested %s: %d new or revised periods", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
