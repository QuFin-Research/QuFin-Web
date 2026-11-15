"""Ingest BLS series (Employment Cost Index) into the point-in-time macro store.

BLS returns current values with no vintages, so each period is dated by its usual
release lag rather than by ALFRED-style real-time periods.
"""

import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from functools import partial

from sqlalchemy.orm import Session

from app.connectors.bls import BlsClient
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "U.S. Bureau of Labor Statistics"
RELEASE = "BLS News Release"

# BLS has no vintages, so each period is dated by its release lag. BLS dates monthly
# periods at the month's first day and quarterly periods at the quarter's first day;
# lags below are measured from that date and err late (rule 9). ECI for Q1 releases at the
# end of April (~119 days after Jan 1). Verify against bls.gov/schedules when adding a series.
DEFAULT_RELEASE_LAG_DAYS = 70  # fallback for a newly added series
RELEASE_LAG_DAYS = {
    "CIS1010000000000I": 125,  # ECI, quarterly: Jan 1 + 125 d = May 6 (end-April release)
}

# BLS series specs: series_id -> (title, units, frequency, seasonal_adjustment)
SERIES: dict[str, dict[str, str]] = {
    "CIS1010000000000I": {
        "title": "Employment Cost Index: Total Compensation, Civilian Workers",
        "units": "Index, Dec 2005=100",
        "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally Adjusted",
    },
}


def _dated_by_lag(period: date, lag: timedelta) -> date:
    return period + lag


def ingest(
    client: BlsClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """Each series in its own transaction; one failure does not stop the rest."""
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results = []
    for i, series_id in enumerate(series_ids):
        entry = BY_ID.get(series_id)
        if entry is None or entry.source != "bls" or series_id not in SERIES:
            results.append(IngestResult(series_id, None, "not a BLS series in the catalog"))
            continue
        if i:
            sleep(1.0)
        spec = SERIES[series_id]
        lag = timedelta(days=RELEASE_LAG_DAYS.get(series_id, DEFAULT_RELEASE_LAG_DAYS))
        try:
            # BLS filters by whole years, so a mid-year start is trimmed here.
            observations = [
                (period, value)
                for period, value in client.series(series_id, start_year=start.year)
                if period >= start
            ]
            meta = SeriesMeta(
                id=series_id,
                source="bls",
                title=spec["title"],
                units=spec["units"],
                frequency=spec["frequency"],
                seasonal_adjustment=spec["seasonal_adjustment"],
                country=entry.country,
                dimension=entry.dimension,
                last_updated=None,
                cycle=entry.cycle,
                source_name=PUBLISHER,
                release_name=RELEASE,
            )
            # BLS has no vintages: date each period by its usual release lag (err late).
            rows = store.record_latest(meta, observations, partial(_dated_by_lag, lag=lag), today)
        except Exception as exc:
            session.rollback()
            log.warning("BLS ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue

        log.info("Ingested %s: %d new or revised periods", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
