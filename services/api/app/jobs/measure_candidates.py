"""Measure each staged candidate against the series that serves its pair (rule 38, "Earliest").

It reads what the loaders stored: the day each candidate period was first read
(`candidate_sightings`) and the first release of each period of the served series (the vintage
store). It compares only periods published after the candidate was first loaded, applies
`app/domain/measurement.py` and prints the verdict. It records no decision: that is a reviewed
change (rules 26 and 38) made from this table.
"""

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.data.candidates import Candidate as RegisteredCandidate
from app.domain.measurement import Measurement, measure, read_period
from app.stores.candidates import CandidateStore
from app.stores.macro import MacroStore


def measure_all(
    session: Session,
    candidates: Iterable[RegisteredCandidate],
    today: date | None = None,
    loaded: Mapping[str, date] | None = None,
) -> list[Measurement]:
    """One measurement per candidate that is stored. `loaded` overrides the day a series was last
    loaded (tests); by default it is the day the series was last ingested."""
    today = today or datetime.now(UTC).date()
    store, sightings = MacroStore(session), CandidateStore(session)
    staged = {s.meta.id: s for s in store.list_series(("staged",))}
    served_rows = {s.meta.id: s for s in store.list_series()}
    found: list[Measurement] = []
    for c in candidates:
        row, served = staged.get(c.id), served_rows.get(c.serves)
        if row is None or served is None:
            found.append(Measurement(c.id, c.serves))
            continue
        seen = {s.period: s for s in sightings.sightings(c.id)}
        bootstrap = [p for p, s in seen.items() if s.bootstrap]
        first = max(bootstrap) if bootstrap else None
        releases = store.first_releases(first or date(1990, 1, 1), c.serves).get(c.serves, {})
        candidate_loaded = (loaded or {}).get(c.id) or row.ingested_at.date()
        served_loaded = (loaded or {}).get(c.serves) or served.ingested_at.date()
        reads = []
        periods = set(releases) | {p for p, s in seen.items() if not s.bootstrap}
        for period in sorted(periods):
            if first is not None and period <= first:
                continue  # published before QuFin looked at the candidate
            sighting = seen.get(period)
            read = read_period(
                period,
                served_read=releases.get(period),
                candidate_read=sighting.first_seen if sighting else None,
                served_loaded=min(served_loaded, today),
                candidate_loaded=min(candidate_loaded, today),
            )
            if read is not None:
                reads.append(read)
        found.append(
            measure(
                c.id,
                c.serves,
                reads,
                served_source=served.meta.source,
                candidate_source=c.source,
                country=c.country,
                served_latest=served.last_period,
                candidate_latest=row.last_period,
            )
        )
    return found
