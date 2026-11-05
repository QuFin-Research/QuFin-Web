"""Ingest euro area series from the ECB Data Portal into the point-in-time macro store."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.ecb import EcbClient
from app.connectors.sdmx import SdmxError
from app.data.ecb_calendar import hicp_release, m3_release, policy_rate_release
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EcbSeries:
    frequency: str
    # Verified from each key's adjustment dimension and the ECB's series notes.
    seasonal_adjustment: str
    source_name: str
    release_name: str
    release_of: Callable[[date], date]


_HICP = EcbSeries(
    "Monthly",
    "Not Seasonally Adjusted",
    "Eurostat",
    "HICP (flash estimate, then final)",
    hicp_release,
)

# Catalog id = dataflow + "." + series key, as the ECB names it.
SERIES: dict[str, EcbSeries] = {
    "FM.D.U2.EUR.4F.KR.DFR.LEV": EcbSeries(
        "Daily",
        "Not Seasonally Adjusted",
        "European Central Bank",
        "Monetary policy decisions",
        policy_rate_release,
    ),
    "HICP.M.U2.N.000000.4D0.ANR": _HICP,
    "HICP.M.U2.N.XEF000.4D0.ANR": _HICP,
    "BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E": EcbSeries(
        "Monthly",
        "Seasonally and Working Day Adjusted",
        "European Central Bank",
        "Monetary developments in the euro area",
        m3_release,
    ),
}


def _units(attributes: dict[str, str]) -> str:
    unit, mult = attributes.get("UNIT", ""), attributes.get("UNIT_MULT", "")
    return f"{mult} of {unit}" if mult and mult != "Units" else unit


def ingest(
    client: EcbClient,
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
        entry, spec = BY_ID.get(series_id), SERIES.get(series_id)
        if entry is None or entry.source != "ecb" or spec is None:
            results.append(IngestResult(series_id, None, "not an ECB series in the catalog"))
            continue
        flow, key = series_id.split(".", 1)
        try:
            fetched = client.series(flow, key, start)
        except SdmxError as exc:
            session.rollback()
            log.warning("ECB ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        meta = SeriesMeta(
            id=series_id,
            source="ecb",
            title=fetched.title,
            units=_units(fetched.attributes),
            frequency=spec.frequency,
            seasonal_adjustment=spec.seasonal_adjustment,
            country=entry.country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name=spec.source_name,
            release_name=spec.release_name,
        )
        # Days with no value (none expected) are not stored as zero or carried forward.
        observations = [(p, v) for p, v in fetched.observations if v is not None]
        rows = store.record_latest(meta, observations, spec.release_of, today)
        log.info("Ingested %s: %d new or revised periods", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
