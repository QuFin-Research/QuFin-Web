"""Promote a staged candidate that won into the catalog (rule 38, "Changing source").

When the measurement says a candidate was earlier, a reviewed pull request adds it to the catalog
under a new series id (rules 26 and 38) and this moves what was already collected into that series,
so nothing is thrown away and re-fetched:

- the values and their vintages, with the days they were first read;
- the first-sight days of `candidate_sightings`, so the measurement's history continues;
- the source decision, recorded from the effective date, which retires the series that served the
  pair (kept read-only for as-of reads before the change, rule 16) and frees its canonical code.

The staged copy is then removed. It never served or scored anything, so no as-of read refers to it.
Everything happens in one transaction: a failure leaves the database as it was.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data.candidates import CANDIDATE_BY_ID
from app.data.macro_catalog import BY_ID
from app.data.taxonomy import TaxonomyError, canonical_code
from app.stores.candidates import CandidateSightingRow
from app.stores.macro import MacroObservationRow, MacroSeriesRow
from app.stores.source_decisions import CONFIRMED, SourceStore

KEEP_BLANK = ("id", "lifecycle", "retired_on", "canonical_code")


class PromotionError(ValueError):
    """A promotion that cannot be made safely; nothing was changed."""


@dataclass(frozen=True)
class Promotion:
    candidate_id: str
    series_id: str
    observations: int
    sightings: int
    retired: str


def promote(
    session: Session,
    candidate_id: str,
    series_id: str,
    effective_from: date,
    *,
    reason: str,
) -> Promotion:
    candidate = CANDIDATE_BY_ID.get(candidate_id)
    if candidate is None:
        raise PromotionError(f"{candidate_id} is not a registered candidate")
    entry = BY_ID.get(series_id)
    if entry is None or entry.source != candidate.source or entry.country != candidate.country:
        raise PromotionError(
            f"{series_id} must be in the catalog with source {candidate.source} and country "
            f"{candidate.country}: add it in a reviewed pull request first"
        )
    if session.get(MacroSeriesRow, series_id) is not None:
        raise PromotionError(f"{series_id} is already stored: a promoted series needs an unused id")
    staged = session.get(MacroSeriesRow, candidate_id)
    if staged is None or staged.lifecycle != "staged":
        raise PromotionError(f"{candidate_id} is not stored as a staged series")
    sources = SourceStore(session)
    current = sources.in_force(candidate.country, candidate.concept, effective_from)
    if current is None or current.series_id != candidate.serves:
        raise PromotionError(f"{candidate.serves} is not the series serving that pair")

    try:
        fields = {
            c.name: getattr(staged, c.name)
            for c in MacroSeriesRow.__table__.columns
            if c.name not in KEEP_BLANK
        }
        new = MacroSeriesRow(id=series_id, lifecycle="live", **fields)
        session.add(new)
        session.flush()
        observations = session.scalars(
            select(MacroObservationRow).where(MacroObservationRow.series_id == candidate_id)
        ).all()
        session.add_all(
            MacroObservationRow(
                series_id=series_id,
                period=o.period,
                realtime_start=o.realtime_start,
                realtime_end=o.realtime_end,
                value=o.value,
            )
            for o in observations
        )
        sightings = session.scalars(
            select(CandidateSightingRow).where(CandidateSightingRow.series_id == candidate_id)
        ).all()
        session.add_all(
            CandidateSightingRow(
                series_id=series_id,
                period=s.period,
                first_seen=s.first_seen,
                bootstrap=s.bootstrap,
            )
            for s in sightings
        )
        session.flush()
        # Retires the series that served the pair and frees its canonical code.
        sources.decide(
            candidate.country,
            candidate.concept,
            series_id,
            candidate.source,
            effective_from,
            reason=reason,
            status=CONFIRMED,
            commit=False,
        )
        try:
            new.canonical_code = canonical_code(
                series_id, new.country, new.frequency, new.seasonal_adjustment
            )
        except TaxonomyError:
            new.canonical_code = None
        for table, column, value in (
            (CandidateSightingRow, CandidateSightingRow.series_id, candidate_id),
            (MacroObservationRow, MacroObservationRow.series_id, candidate_id),
            (MacroSeriesRow, MacroSeriesRow.id, candidate_id),
        ):
            session.execute(delete(table).where(column == value))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return Promotion(candidate_id, series_id, len(observations), len(sightings), candidate.serves)
