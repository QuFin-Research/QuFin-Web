"""Ingest OECD leading indicators and confidence surveys into the point-in-time macro store."""

import logging
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.oecd import CLI_FLOW, OecdClient
from app.connectors.sdmx import SdmxError
from app.data.gap_ids import OECD_FLOW_BY_ID
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, OECD_SERIES, start_for
from app.data.macro_ids import OECD_MACRO, UNE_FLOW, UNE_KEY
from app.data.oecd_calendar import oecd_quarterly_release, oecd_release
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "OECD (from national sources)"
RELEASE = "OECD Composite Leading Indicators"
UNE_RELEASE = "OECD Harmonised Unemployment Rates"
MEASURE_TITLES = {
    "LI": "Composite leading indicator",
    "BCICP": "Business confidence indicator",
    "CCICP": "Consumer confidence indicator",
}
# Index form, amplitude adjusted (long-term average = 100), as checked on 6 Nov 2026.
UNIT, ADJUSTMENT, TRANSFORMATION, METHODOLOGY = "IX", "AA", "IX", "H"


# The OECD limits requests per hour (it answered 429 after about 70 in a row on 6 Nov 2026).
PAUSE_SECONDS = 3.0


def _check_complete(
    series_id: str, observations: Sequence[tuple[date, float]], step: int = 1
) -> None:
    """Every month (or quarter, `step` 3) from the first to the last: a gap means a broken or
    partial response."""
    months = [p.year * 12 + p.month for p, _ in observations]
    if not months:
        raise SdmxError(f"{series_id}: the OECD returned no observations")
    missing = ((months[-1] - months[0]) // step + 1) - len(set(months))
    if missing:
        raise SdmxError(f"{series_id}: {missing} months missing from the OECD response")


def ingest(
    client: OecdClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    today = today or datetime.now(UTC).date()
    wanted = list(series_ids)
    known = {
        sid
        for sid in wanted
        if sid in BY_ID and (sid in OECD_SERIES or sid in OECD_MACRO or sid in OECD_FLOW_BY_ID)
    }
    results = [
        IngestResult(sid, None, "not an OECD series in the catalog")
        for sid in wanted
        if sid not in known
    ]
    if not known:
        return results
    store = MacroStore(session)
    for i, series_id in enumerate(sid for sid in wanted if sid in known):
        if i:
            sleep(PAUSE_SECONDS)  # the OECD rate-limits its API
        # One fully specified key per request: the OECD returns broken partial histories for
        # multi-series queries (checked 6 Nov 2026), so they are never used.
        flow_spec = OECD_FLOW_BY_ID.get(series_id)
        if flow_spec is not None:
            flow, key = flow_spec.flow, flow_spec.key
        elif series_id in OECD_MACRO:
            flow, key = UNE_FLOW, UNE_KEY.format(area=OECD_MACRO[series_id].area)
        else:
            area, measure = OECD_SERIES[series_id]
            flow = CLI_FLOW
            key = f"{area}.M.{measure}.{UNIT}..{ADJUSTMENT}.{TRANSFORMATION}..{METHODOLOGY}"
        try:
            fetched = client.series(flow, key, start_for(series_id, start))
            observations = [(p, v) for p, v in fetched.observations if v is not None]
            _check_complete(
                series_id,
                observations,
                3 if flow_spec and flow_spec.frequency == "Quarterly" else 1,
            )
        except SdmxError as exc:
            session.rollback()
            log.warning("OECD ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        entry = BY_ID[series_id]
        frequency = "Monthly"
        if flow_spec is not None:
            title, units, adjustment = flow_spec.title, flow_spec.units, flow_spec.adjustment
            release = flow_spec.release
            frequency = flow_spec.frequency
        elif series_id in OECD_MACRO:
            area = OECD_MACRO[series_id].area
            title = f"Unemployment rate (ILO definition, ages 15 and over), {area}"
            units, adjustment, release = "Percent", "Seasonally Adjusted", UNE_RELEASE
        else:
            title = f"{MEASURE_TITLES[measure]} (amplitude adjusted), {area}"
            units, adjustment = "Index, long-term average = 100", "Amplitude Adjusted (OECD)"
            release = RELEASE
        meta = SeriesMeta(
            id=series_id,
            source="oecd",
            title=title,
            units=units,
            frequency=frequency,
            seasonal_adjustment=adjustment,
            country=entry.country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name=PUBLISHER,
            release_name=release,
        )
        release_rule = oecd_quarterly_release if frequency == "Quarterly" else oecd_release
        rows = store.record_latest(meta, observations, release_rule, today)
        log.info("Ingested %s: %d new or revised months", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
