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
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.connectors.bls import BlsError
from app.connectors.eurostat import EurostatError
from app.connectors.fred import FredError
from app.connectors.sdmx import SdmxError
from app.data.candidates import CANDIDATES, Candidate
from app.data.eurostat_calendar import release_of as eurostat_release_of
from app.data.imf_calendar import imf_release
from app.data.macro_catalog import DEFAULT_OBSERVATION_START
from app.data.oecd_calendar import oecd_release
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


def _fred_meta(c: Candidate, info: Any) -> SeriesMeta:
    return SeriesMeta(
        id=c.id,
        source="fred",
        title=f"{info.title} (candidate)",
        units=info.units,
        frequency=info.frequency,
        seasonal_adjustment=info.seasonal_adjustment,
        country=c.country,
        dimension="housing",
        last_updated=info.last_updated,
        cycle="leading",
    )


def _load_bls(client: Any, store: MacroStore, c: Candidate, start: date, today: date):
    """BLS serves current values only: a period is first read on the day it first appears. The
    series is described like the one it is timed against."""
    served = store.get_series(c.serves)
    if served is None:
        raise KeyError(f"{c.serves} is not stored, so {c.id} cannot be described")
    observations = [(p, v) for p, v in client.series(c.key, start.year) if v is not None]
    meta = replace(served, id=c.id, source="bls", title=f"{served.title} (BLS candidate)")
    rows = store.record_latest(meta, observations, lambda _p: today, today, STAGED)
    return observations, rows


def _gap_meta(c: Candidate, source_name: str, release: str) -> SeriesMeta:
    return SeriesMeta(
        id=c.id,
        source=c.source,
        title=f"{c.title} (candidate)",
        units=c.units,
        frequency=c.frequency,
        seasonal_adjustment=c.adjustment,
        country=c.country,
        dimension=c.dimension,
        last_updated=None,
        cycle=c.cycle or None,
        source_name=source_name,
        release_name=release,
    )


def _load_eurostat(client: Any, store: MacroStore, c: Candidate, start: date, today: date):
    filters = dict(part.split("=", 1) for part in c.key.split(","))
    fetched = client.series(c.flow, filters, start)
    meta = _gap_meta(c, "Eurostat (from national statistical institutes)", c.flow)
    rows = store.record_latest(
        meta, fetched.observations, eurostat_release_of(c.flow), today, STAGED
    )
    return fetched.observations, rows


def _load_oecd(client: Any, store: MacroStore, c: Candidate, start: date, today: date):
    fetched = client.series(c.flow, c.key, start)
    observations = [(p, v) for p, v in fetched.observations if v is not None]
    meta = _gap_meta(c, "OECD (from national sources)", c.flow)
    rows = store.record_latest(meta, observations, oecd_release, today, STAGED)
    return observations, rows


def _load_fred(client: Any, store: MacroStore, c: Candidate, start: date, today: date):
    """FRED's current value of each period, dated by the first vintage that carried it."""
    info = client.series(c.key)
    vintages = client.vintages(c.key, start)
    first: dict[date, date] = {}
    latest: dict[date, tuple[date, float]] = {}
    for v in vintages:
        if v.value is None:
            continue
        first[v.period] = min(v.realtime_start, first.get(v.period, v.realtime_start))
        if v.period not in latest or v.realtime_start >= latest[v.period][0]:
            latest[v.period] = (v.realtime_start, v.value)
    observations = sorted((p, value) for p, (_, value) in latest.items())
    rows = store.record_latest(
        _fred_meta(c, info), observations, lambda p: first.get(p, today), today, STAGED
    )
    return observations, rows


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
        known = c.source in ("imf", "fred", "bls", "eurostat") or (
            c.source == "oecd" and not c.serves
        )
        if client is None or not known:
            results.append(IngestResult(c.id, None, f"no loader for source {c.source}"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        first_load = store.lifecycle_of(c.id) is None
        try:
            if c.source == "fred":
                observations, rows = _load_fred(client, store, c, start, today)
            elif c.source == "bls":
                observations, rows = _load_bls(client, store, c, start, today)
            elif c.source == "eurostat":
                observations, rows = _load_eurostat(client, store, c, start, today)
            elif c.source == "oecd":
                observations, rows = _load_oecd(client, store, c, start, today)
            else:
                fetched = client.series(c.flow, c.key, start)
                observations = [(p, v) for p, v in fetched.observations if v is not None]
                rows = store.record_latest(_imf_meta(c), observations, imf_release, today, STAGED)
            new = sightings.record(c.id, [p for p, _ in observations], today, bootstrap=first_load)
        except (SdmxError, FredError, BlsError, EurostatError, KeyError) as exc:
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
