"""Source decisions: which source serves each country-indicator pair, and from when (rules 16, P).

A pair is (country, concept). Each decision names the series that serves the pair from
`effective_from`; a change closes the open decision, retires the previous series (kept read-only
for as-of reads before the change) and opens a new one. Reads as of an earlier date resolve to the
series in force then, so past scores and backtests do not change when a source does.

A pair with no decision is served by its catalog series, as before. A provisional decision is the
first one for a pair, made before a release cycle has been measured (rule P); it serves and is
scored like any other, and scores record it (rule 20).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.stores.db import Base
from app.stores.macro import MacroSeriesRow

PROVISIONAL, CONFIRMED = "provisional", "confirmed"
LIVE, RETIRED, STAGED = "live", "retired", "staged"


class SourceDecisionRow(Base):
    __tablename__ = "source_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(2))
    concept: Mapped[str] = mapped_column(String(64))
    series_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(16))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_source_decisions_pair", "country", "concept", "effective_from"),)


@dataclass(frozen=True)
class SourceDecision:
    country: str
    concept: str
    series_id: str
    source: str
    effective_from: date
    effective_to: date | None
    status: str
    reason: str


def _decision(row: SourceDecisionRow) -> SourceDecision:
    return SourceDecision(
        row.country,
        row.concept,
        row.series_id,
        row.source,
        row.effective_from,
        row.effective_to,
        row.status,
        row.reason,
    )


class SourceStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def history(self, country: str, concept: str) -> list[SourceDecision]:
        rows = self.session.scalars(
            select(SourceDecisionRow)
            .where(SourceDecisionRow.country == country, SourceDecisionRow.concept == concept)
            .order_by(SourceDecisionRow.effective_from, SourceDecisionRow.id)
        )
        return [_decision(r) for r in rows]

    def all(self) -> list[SourceDecision]:
        rows = self.session.scalars(
            select(SourceDecisionRow).order_by(
                SourceDecisionRow.country,
                SourceDecisionRow.concept,
                SourceDecisionRow.effective_from,
                SourceDecisionRow.id,
            )
        )
        return [_decision(r) for r in rows]

    def in_force(self, country: str, concept: str, as_of: date) -> SourceDecision | None:
        """The decision that served the pair on `as_of`, or None before the first one."""
        found = None
        for d in self.history(country, concept):
            if d.effective_from <= as_of and (d.effective_to is None or as_of < d.effective_to):
                found = d
        return found

    def series_in_force(self, series_id: str, country: str, as_of: date) -> str:
        """The series that serves `series_id`'s pair on `as_of`; `series_id` if no decision."""
        concept = SERIES_CONCEPTS.get((country, series_id))
        if concept is None:
            return series_id
        decision = self.in_force(country, concept, as_of)
        return decision.series_id if decision else series_id

    def decide(
        self,
        country: str,
        concept: str,
        series_id: str,
        source: str,
        effective_from: date,
        *,
        reason: str,
        status: str = CONFIRMED,
        recorded_at: datetime | None = None,
    ) -> SourceDecision:
        """Record that `series_id` serves the pair from `effective_from`.

        The open decision, if any, ends on that date and its series is retired. Raises ValueError
        for a date before the open decision started, or a status that is not known.
        """
        if status not in (PROVISIONAL, CONFIRMED):
            raise ValueError(f"unknown status {status!r}")
        history = self.history(country, concept)
        current = history[-1] if history and history[-1].effective_to is None else None
        if current is not None:
            if effective_from < current.effective_from:
                raise ValueError("a source decision cannot start before the one it replaces")
            if current.series_id == series_id:
                raise ValueError(f"{series_id} already serves {country} {concept}")
            self.session.execute(
                update(SourceDecisionRow)
                .where(
                    SourceDecisionRow.country == country,
                    SourceDecisionRow.concept == concept,
                    SourceDecisionRow.effective_to.is_(None),
                )
                .values(effective_to=effective_from)
            )
            self._lifecycle(current.series_id, RETIRED, effective_from)
        row = SourceDecisionRow(
            country=country,
            concept=concept,
            series_id=series_id,
            source=source,
            effective_from=effective_from,
            effective_to=None,
            status=status,
            reason=reason,
            recorded_at=recorded_at or datetime.now(UTC),
        )
        self.session.add(row)
        self._lifecycle(series_id, LIVE, None)
        self.session.commit()
        return _decision(row)

    def confirm(self, country: str, concept: str) -> None:
        """The measured winner is the provisional source: the decision stands (rule P)."""
        self.session.execute(
            update(SourceDecisionRow)
            .where(
                SourceDecisionRow.country == country,
                SourceDecisionRow.concept == concept,
                SourceDecisionRow.effective_to.is_(None),
                SourceDecisionRow.status == PROVISIONAL,
            )
            .values(status=CONFIRMED)
        )
        self.session.commit()

    def stage(self, series_id: str) -> None:
        """Mark a candidate series as staged: loaded and timed, never served or scored."""
        self._lifecycle(series_id, STAGED, None)
        self.session.commit()

    def _lifecycle(self, series_id: str, lifecycle: str, retired_on: date | None) -> None:
        values: dict[str, object] = {"lifecycle": lifecycle, "retired_on": retired_on}
        if lifecycle == RETIRED:
            # The canonical code names one live series per country and indicator (a unique
            # index), and the series that replaces this one takes it.
            values["canonical_code"] = None
        self.session.execute(
            update(MacroSeriesRow).where(MacroSeriesRow.id == series_id).values(**values)
        )

    def retired_pairs(self) -> set[frozenset[str]]:
        """Pairs of series expected to carry the same data, exempt from the duplicate check:
        a retired series and each later series of its own pair (rule 16). Nothing else."""
        pairs: set[frozenset[str]] = set()
        grouped: dict[tuple[str, str], list[SourceDecision]] = {}
        for d in self.all():
            grouped.setdefault((d.country, d.concept), []).append(d)
        for decisions in grouped.values():
            for i, older in enumerate(decisions):
                if older.effective_to is None:
                    continue
                for newer in decisions[i + 1 :]:
                    if newer.series_id != older.series_id:
                        pairs.add(frozenset((older.series_id, newer.series_id)))
        return pairs
