"""From a measurement to a source decision (rule 38).

`measure-candidates` says which source was earlier. This turns that into what rule 38 does with it:

- the series that serves the pair was earlier or tied on the more native source: the provisional
  decision is **confirmed**;
- the candidate was earlier: the candidate **replaces** it, which is a change of source. That needs
  a catalog entry, so it is a reviewed pull request (rules 26 and 38), not something a command does;
  `promote-candidate` then moves the staged history into the new series;
- no period has been read on both sides yet: **wait**. A verdict that rests only on a lower bound
  (a source that has not published yet) is shown but not acted on.

The plan changes nothing. `apply` records only confirmations, and only in the database it runs on;
to make one permanent for every database, set `status` in `app/data/source_baseline.py`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.data.candidates import Candidate
from app.domain.measurement import Measurement
from app.jobs.measure_candidates import measure_all
from app.stores.source_decisions import CONFIRMED, PROVISIONAL, SourceStore

CONFIRM, REPLACE, WAIT, SETTLED, NO_DECISION = (
    "confirm",
    "replace",
    "wait",
    "settled",
    "no decision",
)
ACTIONS = (CONFIRM, REPLACE, WAIT, SETTLED, NO_DECISION)


@dataclass(frozen=True)
class Outcome:
    candidate: Candidate
    measurement: Measurement
    action: str
    status: str | None  # the decision's status now: provisional or confirmed
    why: str


def _evidence(m: Measurement) -> bool:
    """At least one period was read on both sides: a lower bound alone is not a measurement."""
    return any(not r.bound for r in m.periods)


def plan(
    session: Session,
    candidates: Iterable[Candidate],
    today: date | None = None,
    loaded: dict[str, date] | None = None,
) -> list[Outcome]:
    today = today or datetime.now(UTC).date()
    sources = SourceStore(session)
    items = [c for c in candidates if c.serves]
    outcomes = []
    for c, m in zip(items, measure_all(session, items, today, loaded), strict=True):
        decision = sources.in_force(c.country, c.concept, today)
        if decision is None or decision.series_id != c.serves:
            outcomes.append(Outcome(c, m, NO_DECISION, None, f"{c.serves} is not what serves it"))
        elif m.recommendation == "insufficient":
            outcomes.append(
                Outcome(c, m, WAIT, decision.status, "no period published since staging")
            )
        elif not _evidence(m):
            outcomes.append(
                Outcome(c, m, WAIT, decision.status, "the candidate has not published a period yet")
            )
        elif m.recommendation == "replace":
            outcomes.append(Outcome(c, m, REPLACE, decision.status, "the candidate was earlier"))
        elif decision.status == CONFIRMED:
            outcomes.append(Outcome(c, m, SETTLED, CONFIRMED, "measured again, still the earliest"))
        else:
            outcomes.append(Outcome(c, m, CONFIRM, PROVISIONAL, m.verdict))
    return outcomes


def apply(session: Session, outcomes: Iterable[Outcome]) -> list[Outcome]:
    """Confirm the provisional decisions the measurement supports. Nothing else is changed."""
    sources = SourceStore(session)
    done = []
    for o in outcomes:
        if o.action == CONFIRM:
            sources.confirm(o.candidate.country, o.candidate.concept)
            done.append(o)
    return done
