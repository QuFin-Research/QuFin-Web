"""Ingest Treasury Fiscal Data series into the point-in-time macro store."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.connectors.treasury import TreasuryClient, TreasuryError
from app.data.macro_catalog import BY_ID, DEFAULT_OBSERVATION_START
from app.data.treasury_calendar import debt_to_penny_release, monthly_release
from app.jobs.ingest_fred import IngestResult
from app.stores.macro import MacroStore, SeriesMeta

log = logging.getLogger(__name__)

PUBLISHER = "U.S. Department of the Treasury, Bureau of the Fiscal Service"


@dataclass(frozen=True)
class TreasurySeries:
    title: str
    units: str
    frequency: str
    release_name: str
    fetch: Callable[[TreasuryClient, date], list[tuple[date, float]]]
    release_of: Callable[[date], date]


SERIES: dict[str, TreasurySeries] = {
    "TREAS_DEBT_TOTAL": TreasurySeries(
        "Total Public Debt Outstanding",
        "Dollars",
        "Daily",
        "Debt to the Penny",
        lambda client, start: client.total_public_debt(start),
        debt_to_penny_release,
    ),
    "TREAS_AVG_RATE_MARKETABLE": TreasurySeries(
        "Average Interest Rate on Total Marketable Treasury Securities",
        "Percent",
        "Monthly",
        "Average Interest Rates on U.S. Treasury Securities",
        lambda client, start: client.average_interest_rate("Total Marketable", start),
        monthly_release,
    ),
    "TREAS_INTEREST_EXPENSE": TreasurySeries(
        "Interest Expense on the Public Debt Outstanding (Monthly Total)",
        "Dollars",
        "Monthly",
        "Interest Expense on the Public Debt Outstanding",
        lambda client, start: client.interest_expense(start),
        monthly_release,
    ),
}


def ingest(
    client: TreasuryClient,
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
        if entry is None or entry.source != "treasury" or spec is None:
            results.append(IngestResult(series_id, None, "not a Treasury series in the catalog"))
            continue
        try:
            observations = spec.fetch(client, start)
        except TreasuryError as exc:
            session.rollback()
            log.warning("Treasury ingest of %s failed: %s", series_id, exc)
            results.append(IngestResult(series_id, None, str(exc)))
            continue
        meta = SeriesMeta(
            id=series_id,
            source="treasury",
            title=spec.title,
            units=spec.units,
            frequency=spec.frequency,
            seasonal_adjustment="Not Seasonally Adjusted",
            country=entry.country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name=PUBLISHER,
            release_name=spec.release_name,
        )
        rows = store.record_latest(meta, observations, spec.release_of, today)
        log.info("Ingested %s: %d new or revised periods", series_id, rows)
        results.append(IngestResult(series_id, rows))
    store.analyze()
    return results
