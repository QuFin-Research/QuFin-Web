"""Candidate sources: series that publish a pair another series serves (rules 37 and 38).

A candidate is loaded without being served (`staged`, Part 0) so its release timing can be measured
against the series that serves the pair, over a release cycle. It is not in the catalog: nothing
refreshes it as a served series, the API never returns it, and the duplicate check and the scorecard
leave it out. If it wins, a reviewed pull request adds it to the catalog and records the source
decision (rules 26 and 38).

Slice 1 covers the pairs whose source decision is still provisional, the 32 consumer price pairs
that moved from the IMF to Eurostat's HICP on 19 Nov 2026 (`app/data/source_baseline.py`): the IMF
series that served them is staged again, under a new id, so the December release can be timed on
both sides. The candidates of the other pairs follow as their sources are measured.
"""

from dataclasses import dataclass

from app.data.macro_ids import IMF_CPI_FLOW, IMF_CPI_KEY
from app.data.source_baseline import BASELINE, CONCEPT
from app.domain.source_selection import Producer

PREFIX = "CAND_"


@dataclass(frozen=True)
class Candidate:
    id: str  # CAND_<SOURCE>_<MEASURE>_<AREA>: never a catalog id
    country: str  # ISO 3166 alpha-2
    concept: str
    source: str
    producer: Producer  # how native it is for this economy (Part 0)
    area: str  # the source's own area code
    serves: str  # the series serving the pair now
    flow: str  # the source's dataset
    key: str  # the source's series key


def _imf_cpi() -> tuple[Candidate, ...]:
    found = []
    for b in BASELINE:
        before = b.predecessor
        if before is None or before.source != "imf" or b.concept != CONCEPT:
            continue
        area = before.series_id.removeprefix("IMF_CPI_")
        found.append(
            Candidate(
                id=f"{PREFIX}IMF_CPI_{area}",
                country=b.country,
                concept=b.concept,
                source="imf",
                producer="global",
                area=area,
                serves=b.series_id,
                flow=IMF_CPI_FLOW,
                key=IMF_CPI_KEY.format(area=area),
            )
        )
    return tuple(found)


CANDIDATES: tuple[Candidate, ...] = _imf_cpi()
CANDIDATE_BY_ID = {c.id: c for c in CANDIDATES}
