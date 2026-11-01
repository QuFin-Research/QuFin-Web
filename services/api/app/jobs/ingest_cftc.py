"""Ingest CFTC Commitments of Traders reports for every QuFin asset."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.connectors.cftc import CftcClient, CftcError
from app.data.positioning_catalog import BY_SYMBOL, DEFAULT_COT_START
from app.stores.positioning import PositioningStore

log = logging.getLogger(__name__)

# Re-read the last few weeks on every run to pick up any re-published report.
OVERLAP = timedelta(weeks=4)


@dataclass(frozen=True)
class CotIngestResult:
    symbol: str
    rows: int | None
    error: str | None = None


def ingest(
    client: CftcClient,
    session: Session,
    symbols: Iterable[str],
    start: date = DEFAULT_COT_START,
    full: bool = False,
) -> list[CotIngestResult]:
    store = PositioningStore(session)
    if corrected := store.correct_release_dates():
        log.warning("Corrected %d stored CFTC release dates to the CFTC calendar", corrected)
    results = []
    for symbol in symbols:
        contract = BY_SYMBOL.get(symbol)
        if contract is None:
            results.append(CotIngestResult(symbol, None, "no CFTC contract mapped"))
            continue
        latest = None if full else store.latest_report_date(contract.code)
        since = max(start, latest - OVERLAP) if latest else start
        try:
            rows = store.upsert(client.reports(contract.code, since))
        except CftcError as exc:
            session.rollback()
            log.warning("CFTC ingest of %s failed: %s", symbol, exc)
            results.append(CotIngestResult(symbol, None, str(exc)))
            continue
        log.info("Ingested %s (%s): %d weekly reports since %s", symbol, contract.code, rows, since)
        results.append(CotIngestResult(symbol, rows))
    return results
