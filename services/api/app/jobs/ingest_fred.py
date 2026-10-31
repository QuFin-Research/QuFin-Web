"""Ingest FRED/ALFRED series (metadata and full vintage history) into the macro store."""

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.connectors.fred import FredClient, FredError
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, CatalogSeries
from app.stores.macro import MacroStore, SeriesMeta, Vintage

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
    if entry.market:
        vintages = date_pre_archive_periods(vintages)
    meta = SeriesMeta(
        id=info.id,
        source=entry.source,
        title=info.title,
        units=info.units,
        frequency=info.frequency,
        seasonal_adjustment=info.seasonal_adjustment,
        country=entry.country,
        dimension=entry.dimension,
        cycle=entry.cycle,
        last_updated=info.last_updated,
    )
    return store.replace_series(meta, vintages)


def date_pre_archive_periods(vintages: Sequence[Vintage]) -> list[Vintage]:
    """Give periods older than the ALFRED archive a release date from the series' usual lag.

    ALFRED's first vintage holds the whole back history as if it were all published that day,
    which would hide years of an unrevised market series from point-in-time queries. Those
    periods are instead treated as published after the 95th percentile of the lag seen
    between a period and its first release once archiving began (a cautious estimate).
    """
    if not vintages:
        return list(vintages)
    archive_start = min(v.realtime_start for v in vintages)
    first_release: dict[date, Vintage] = {}
    for v in vintages:
        if (
            v.period not in first_release
            or v.realtime_start < first_release[v.period].realtime_start
        ):
            first_release[v.period] = v
    lags = sorted(
        (v.realtime_start - v.period).days
        for v in first_release.values()
        if v.realtime_start > archive_start and v.realtime_start >= v.period
    )
    if not lags:
        return list(vintages)
    lag = timedelta(days=lags[min(len(lags) - 1, int(len(lags) * 0.95))])
    result = []
    for v in vintages:
        if v is first_release[v.period] and v.realtime_start == archive_start:
            known = v.period + lag
            if known < archive_start:
                v = replace(v, realtime_start=known)
        result.append(v)
    return result


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
