"""Ingest EIA Weekly Petroleum Status Report series into the point-in-time macro store."""

import logging
from collections.abc import Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.eia import EiaClient, EiaError
from app.data.eia_calendar import wpsr_release_date
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "U.S. Energy Information Administration"
RELEASE = "Weekly Petroleum Status Report"


def ingest(
    client: EiaClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
) -> list[IngestResult]:
    """Each series in its own transaction; one failure does not stop the rest."""
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results = []
    for series_id in series_ids:
        entry = BY_ID.get(series_id)
        if entry is None or entry.source != "eia":
            results.append(IngestResult(series_id, None, "not an EIA series in the catalog"))
            continue
        try:
            fetched = client.weekly_petroleum(series_id, start)
        except EiaError as exc:
            session.rollback()
            log.warning("EIA ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        meta = SeriesMeta(
            id=series_id,
            source="eia",
            title=fetched.title,
            units=fetched.units,
            frequency="Weekly",
            seasonal_adjustment="Not Seasonally Adjusted",
            country=entry.country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name=PUBLISHER,
            release_name=RELEASE,
        )
        rows = store.record_latest(meta, fetched.observations, wpsr_release_date, today)
        log.info("Ingested %s: %d new or revised weeks", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
