"""Load the candidate sources of `app/data/candidates.py` without serving them (rule 38, staging).

Each candidate is stored as a `staged` series under its own id, so it never holds the canonical code
of the series that serves its pair, never appears in a list of served series, and is left out of the
duplicate check and every score. Alongside the values the loader notes the day each period was first
read (`candidate_sightings`): that is what the measurement of "earliest" uses, because the vintage
store dates a late period by its derived release date.

A candidate that fails to load is reported and does not fail a run: staged series are measured, not
relied on (rule 2).
"""

import logging
import time
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.connectors.sdmx import SdmxError
from app.data.candidates import CANDIDATES, Candidate
from app.data.imf_calendar import imf_release
from app.data.macro_catalog import DEFAULT_OBSERVATION_START
from app.jobs.ingest_fred import IngestResult
from app.stores.candidates import CandidateSightingRow, CandidateStore
from app.stores.macro import MacroObservationRow, MacroSeriesRow, MacroStore, SeriesMeta

log = logging.getLogger(__name__)

STAGED = "staged"
CPI_PUBLISHER = "International Monetary Fund (from national statistics offices)"
CPI_RELEASE = "Consumer Price Index (IMF)"
PAUSE_SECONDS = 1.0


def _imf_meta(c: Candidate) -> SeriesMeta:
    return SeriesMeta(
        id=c.id,
        source="imf",
        title=f"Consumer prices (all items, annual rate of change), {c.area} (candidate)",
        units="Percentage change",
        frequency="Monthly",
        seasonal_adjustment="Not Seasonally Adjusted",
        country=c.country,
        dimension="inflation",
        last_updated=None,
        cycle="lagging",
        source_name=CPI_PUBLISHER,
        release_name=CPI_RELEASE,
    )


def ingest(
    clients: Mapping[str, Any],
    session: Session,
    candidates: Iterable[Candidate],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """Each candidate in its own request and transaction; one failure does not stop the rest."""
    today = today or datetime.now(UTC).date()
    store, sightings = MacroStore(session), CandidateStore(session)
    results: list[IngestResult] = []
    for i, c in enumerate(candidates):
        client = clients.get(c.source)
        if client is None or c.source != "imf":
            results.append(IngestResult(c.id, None, f"no loader for source {c.source}"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        first_load = store.lifecycle_of(c.id) is None
        try:
            fetched = client.series(c.flow, c.key, start)
            observations = [(p, v) for p, v in fetched.observations if v is not None]
            rows = store.record_latest(_imf_meta(c), observations, imf_release, today, STAGED)
            new = sightings.record(c.id, [p for p, _ in observations], today, bootstrap=first_load)
        except (SdmxError, KeyError) as exc:
            session.rollback()
            log.warning("staged load of %s failed: %s", c.id, exc)
            results.append(IngestResult(c.id, None, str(exc)))
            continue
        log.info("Staged %s: %d new or revised months, %d first sightings", c.id, rows, new)
        results.append(IngestResult(c.id, rows))
    store.analyze()
    return results


def staging_due(session: Session, today: date, registered: Iterable[str] | None = None) -> bool:
    """Whether a refresh should load the staged candidates: some registered ones are stored and
    one was not loaded today (a monthly series is not fetched more than once a day, rule 28)."""
    ids = {c.id for c in CANDIDATES} if registered is None else set(registered)
    staged = [s for s in MacroStore(session).list_series((STAGED,)) if s.meta.id in ids]
    return bool(staged) and any(s.ingested_at.date() < today for s in staged)


def stale_staged(session: Session, registered: Iterable[str] | None = None) -> list[str]:
    """Staged series no candidate in the registry names any more (for example after rule 38 made
    the bloc aggregator first for their pair)."""
    ids = {c.id for c in CANDIDATES} if registered is None else set(registered)
    return [s.meta.id for s in MacroStore(session).list_series((STAGED,)) if s.meta.id not in ids]


def prune_staged(session: Session, series_ids: Iterable[str]) -> int:
    """Delete staged series, their values and first-read days. Only staged ones: a staged series
    never served or scored anything, so no as-of read refers to it."""
    removed = 0
    for series_id in series_ids:
        row = session.get(MacroSeriesRow, series_id)
        if row is None or row.lifecycle != STAGED:
            continue
        for table, column in (
            (CandidateSightingRow, CandidateSightingRow.series_id),
            (MacroObservationRow, MacroObservationRow.series_id),
            (MacroSeriesRow, MacroSeriesRow.id),
        ):
            session.execute(delete(table).where(column == series_id))
        removed += 1
    session.commit()
    return removed
