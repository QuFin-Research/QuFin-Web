"""Ingest World Bank annual indicators into the point-in-time macro store.

One request per indicator and batch of at most ten countries. The World Bank gives current values
with no vintages, so each year is dated by the release rule (`worldbank_calendar.py`).
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.worldbank import MAX_COUNTRIES_PER_REQUEST, WorldBankClient, WorldBankError
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START, start_for
from app.data.worldbank_calendar import annual_release
from app.data.worldbank_ids import WB_BY_ID
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "World Bank (from national sources)"
RELEASE = "World Development Indicators"
PAUSE_SECONDS = 3.0


def ingest(
    client: WorldBankClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """One request per indicator and ten countries; each series in its own commit."""
    today = today or datetime.now(UTC).date()
    wanted = list(series_ids)
    results = [
        IngestResult(sid, None, "not a World Bank series in the catalog")
        for sid in wanted
        if sid not in WB_BY_ID or sid not in BY_ID
    ]
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in wanted:
        if sid in WB_BY_ID and sid in BY_ID:
            groups[WB_BY_ID[sid].indicator.code].append(sid)
    store = MacroStore(session)
    refused = False
    requests = 0
    for code, ids in groups.items():
        for i in range(0, len(ids), MAX_COUNTRIES_PER_REQUEST):
            batch = ids[i : i + MAX_COUNTRIES_PER_REQUEST]
            if refused:
                results.extend(
                    IngestResult(sid, None, "not requested: the World Bank refused a request")
                    for sid in batch
                )
                continue
            if requests:
                sleep(PAUSE_SECONDS)
            requests += 1
            countries = [WB_BY_ID[sid].iso3 for sid in batch]
            try:
                fetched = client.indicator(
                    code, countries, min(start_for(sid, start) for sid in batch)
                )
            except WorldBankError as exc:
                log.warning("World Bank request for %s failed: %s", code, exc)
                results.extend(IngestResult(sid, None, str(exc)) for sid in batch)
                refused = "refused" in str(exc) or "429" in str(exc) or "403" in str(exc)
                continue
            for sid in batch:
                spec = WB_BY_ID[sid]
                entry = BY_ID[sid]
                first = start_for(sid, start)
                observations = [(p, v) for p, v in fetched.get(spec.iso3, []) if p >= first]
                if not observations:
                    results.append(
                        IngestResult(sid, None, f"{sid}: the World Bank returned no observations")
                    )
                    continue
                meta = SeriesMeta(
                    id=sid,
                    source="worldbank",
                    title=spec.indicator.title,
                    units=spec.indicator.units,
                    frequency="Annual",
                    seasonal_adjustment="Not Seasonally Adjusted",
                    country=entry.country,
                    dimension=entry.dimension,
                    last_updated=None,
                    cycle=entry.cycle,
                    source_name=PUBLISHER,
                    release_name=RELEASE,
                )
                rows = store.record_latest(meta, observations, annual_release, today)
                log.info("Ingested %s: %d new or revised years", sid, rows)
                results.append(IngestResult(sid, rows))
    store.analyze()
    return results
