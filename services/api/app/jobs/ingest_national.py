"""Ingest national-portal series (Rule O tier 3): Brazil's SGS and Singapore's Table Builder.

Both give current values with no vintages, so each period is dated by its usual release lag
(`app/data/national_calendar.py`), erring late.
"""

import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.bcb import BcbClient, BcbError
from app.connectors.singstat import SingStatClient, SingStatError
from app.data.gap_ids import BCB_BY_ID, BCB_COUNTRY, SINGSTAT_BY_ID, SINGSTAT_COUNTRY
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, start_for
from app.data.national_calendar import brazil_release, singapore_quarterly_release
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

BCB_PUBLISHER = "Banco Central do Brasil (from IBGE and its own statistics)"
SINGSTAT_PUBLISHER = "Singapore Department of Statistics"
PAUSE_SECONDS = 2.0


def ingest_bcb(
    client: BcbClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results: list[IngestResult] = []
    for i, series_id in enumerate(series_ids):
        spec = BCB_BY_ID.get(series_id)
        entry = BY_ID.get(series_id)
        if spec is None or entry is None or entry.source != "bcb":
            results.append(IngestResult(series_id, None, "not a BCB series in the catalog"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        try:
            observations = client.series(spec.code, start_for(series_id, start), today)
            meta = SeriesMeta(
                id=series_id,
                source="bcb",
                title=spec.title,
                units=spec.units,
                frequency="Monthly",
                seasonal_adjustment=spec.adjustment,
                country=BCB_COUNTRY,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=BCB_PUBLISHER,
                release_name=spec.release,
            )
            rows = store.record_latest(meta, observations, brazil_release, today)
        except BcbError as exc:
            session.rollback()
            log.warning("BCB ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        log.info("Ingested %s: %d new or revised months", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results


def ingest_singstat(
    client: SingStatClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results: list[IngestResult] = []
    for i, series_id in enumerate(series_ids):
        spec = SINGSTAT_BY_ID.get(series_id)
        entry = BY_ID.get(series_id)
        if spec is None or entry is None or entry.source != "singstat":
            results.append(IngestResult(series_id, None, "not a SingStat series in the catalog"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        try:
            observations = client.series(spec.table, spec.series_no, start_for(series_id, start))
            meta = SeriesMeta(
                id=series_id,
                source="singstat",
                title=spec.title,
                units=spec.units,
                frequency="Quarterly",
                seasonal_adjustment="Seasonally Adjusted",
                country=SINGSTAT_COUNTRY,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=SINGSTAT_PUBLISHER,
                release_name=spec.release,
            )
            rows = store.record_latest(meta, observations, singapore_quarterly_release, today)
        except SingStatError as exc:
            session.rollback()
            log.warning("SingStat ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        log.info("Ingested %s: %d new or revised quarters", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
