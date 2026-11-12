"""Ingest BIS series (policy rates, effective exchange rates, credit) into the macro store."""

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.bis import BisClient
from app.connectors.sdmx import SdmxError, SdmxSeries
from app.data.bis_calendar import monthly_release, quarterly_release
from app.data.bis_ids import BIS_SERIES, KNOWN_GAPS, MEASURES, BisMeasure
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "Bank for International Settlements (from national central banks)"
RELEASES = {
    "WS_CBPOL": "BIS Central bank policy rates",
    "WS_EER": "BIS Effective exchange rates",
    "WS_CREDIT_GAP": "BIS Credit-to-GDP gaps",
}
PAUSE_SECONDS = 1.0


def _check_complete(series_id: str, measure: BisMeasure, periods: Sequence[date]) -> None:
    """Every month or quarter from the first to the last: a gap means a partial response."""
    if not periods:
        raise SdmxError(f"{series_id}: the BIS returned no observations")
    step = 1 if measure.frequency == "Monthly" else 3
    have = {p.year * 12 + p.month - 1 for p in periods}
    allowed = [
        (a.year * 12 + a.month - 1, b.year * 12 + b.month - 1)
        for a, b in KNOWN_GAPS.get(series_id, ())
    ]
    missing = [
        m
        for m in range(min(have), max(have) + 1, step)
        if m not in have and not any(lo <= m <= hi for lo, hi in allowed)
    ]
    if missing:
        raise SdmxError(f"{series_id}: {len(missing)} periods missing from the BIS response")


def _check_units(series_id: str, measure: BisMeasure, fetched: SdmxSeries) -> None:
    """The units text was verified against the BIS's own; a change must fail, not load."""
    stated = fetched.attributes.get("UNIT_MEASURE")
    if measure.unit_measure and stated != measure.unit_measure:
        raise SdmxError(f"{series_id}: BIS units are {stated!r}, expected {measure.unit_measure!r}")


def ingest(
    client: BisClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """One request per measure (all its economies at once); each series in its own commit."""
    today = today or datetime.now(UTC).date()
    wanted = list(series_ids)
    results = [
        IngestResult(sid, None, "not a BIS series in the catalog")
        for sid in wanted
        if sid not in BIS_SERIES or sid not in BY_ID
    ]
    by_measure: dict[str, list[str]] = defaultdict(list)
    for sid in wanted:
        if sid in BIS_SERIES and sid in BY_ID:
            by_measure[BIS_SERIES[sid][0]].append(sid)
    store = MacroStore(session)
    for i, (code, ids) in enumerate(by_measure.items()):
        measure = MEASURES[code]
        if i:
            sleep(PAUSE_SECONDS)
        areas = "+".join(BIS_SERIES[sid][1] for sid in ids)
        try:
            fetched = {
                s.dimensions.get(measure.area_dimension, ""): s
                for s in client.many(measure.flow, measure.key.format(areas=areas), start)
            }
        except SdmxError as exc:
            log.warning("BIS request for %s failed: %s", code, exc)
            results.extend(IngestResult(sid, None, str(exc)) for sid in ids)
            continue
        release_of = monthly_release if measure.frequency == "Monthly" else quarterly_release
        for series_id in ids:
            area = BIS_SERIES[series_id][1]
            try:
                series = fetched.get(area)
                if series is None:
                    raise SdmxError(f"{series_id}: the BIS returned no series for {area}")
                _check_units(series_id, measure, series)
                observations = [(p, v) for p, v in series.observations if v is not None]
                _check_complete(series_id, measure, [p for p, _ in observations])
            except SdmxError as exc:
                session.rollback()
                log.warning("BIS ingest of %s failed: %s", series_id, exc)
                results.append(IngestResult(series_id, None, str(exc)))
                continue
            entry = BY_ID[series_id]
            meta = SeriesMeta(
                id=series_id,
                source="bis",
                title=f"{measure.title}, {area}",
                units=measure.units,
                frequency=measure.frequency,
                seasonal_adjustment=measure.seasonal_adjustment,
                country=entry.country,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=PUBLISHER,
                release_name=RELEASES[measure.flow],
            )
            rows = store.record_latest(meta, observations, release_of, today)
            log.info("Ingested %s: %d new or revised periods", series_id, rows)
            results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
