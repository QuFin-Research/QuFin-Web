"""Ingest IMF series (International Liquidity) into the point-in-time macro store."""

import logging
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.imf import IL_FLOW, ImfClient
from app.connectors.sdmx import SdmxError
from app.data.imf_calendar import imf_release
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.data.reserves_ids import IMF_RESERVES
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "International Monetary Fund (from national central banks)"
RELEASE = "International Liquidity (IMF)"
INDICATOR = "RXF11_REVS"  # reserves excluding gold
# The IMF's UNIT dimension, as the units text QuFin stores. Values come in units of the
# currency: the SCALE attribute ("Millions") is a display hint only, checked against FRED's
# copies on 7 Nov 2026, so nothing is rescaled.
UNITS = {"USD": "U.S. Dollars"}
PAUSE_SECONDS = 1.0


def ingest(
    client: ImfClient,
    session: Session,
    series_ids: Iterable[str],
    start: date = DEFAULT_OBSERVATION_START,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[IngestResult]:
    """Each series in its own request and transaction; one failure does not stop the rest."""
    today = today or datetime.now(UTC).date()
    store = MacroStore(session)
    results = []
    for i, series_id in enumerate(series_ids):
        entry, area = BY_ID.get(series_id), IMF_RESERVES.get(series_id)
        if entry is None or entry.source != "imf" or area is None:
            results.append(IngestResult(series_id, None, "not an IMF series in the catalog"))
            continue
        if i:
            sleep(PAUSE_SECONDS)
        try:
            fetched = client.series(IL_FLOW, f"{area}.{INDICATOR}.USD.M", start)
            units = UNITS[fetched.dimensions.get("UNIT", "USD")]
        except (SdmxError, KeyError) as exc:
            session.rollback()
            log.warning("IMF ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        meta = SeriesMeta(
            id=series_id,
            source="imf",
            title=f"Reserves excluding gold, {area}",
            units=units,
            frequency="Monthly",
            seasonal_adjustment="Not Seasonally Adjusted",
            country=entry.country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name=PUBLISHER,
            release_name=RELEASE,
        )
        observations = [(p, v) for p, v in fetched.observations if v is not None]
        rows = store.record_latest(meta, observations, imf_release, today)
        log.info("Ingested %s: %d new or revised months", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
