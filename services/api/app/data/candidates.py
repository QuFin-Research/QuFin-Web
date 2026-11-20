"""Candidate sources: series that publish a pair another series serves (rules 37 and 38).

A candidate is loaded without being served (`staged`, Part 0) so its release timing can be measured
against the series that serves the pair, over a release cycle. It is not in the catalog: nothing
refreshes it as a served series, the API never returns it, and the duplicate check and the scorecard
leave it out. If it wins, a reviewed pull request adds it to the catalog and records the source
decision (rules 26 and 38).

The registry holds the pairs the measures still decide: the United States and every economy
Eurostat does not serve. Slice 1 staged 32 IMF consumer price series for the pairs moved to
Eurostat's HICP on 19 Nov 2026; rule 38's *Bloc aggregator first* (v3.5) makes Eurostat the source
of those pairs whatever the IMF's timing, so they were removed. Candidates are added here as other
pairs are measured.
"""

from dataclasses import dataclass

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
    key: str  # the source's series key (FRED: the series id)
    months: int = 1  # months in a period: 1 monthly, 3 quarterly


CANDIDATES: tuple[Candidate, ...] = (
    # The United States' commercial property prices: the BIS serves the pair (provisional since
    # 19 Nov 2026); FRED's copy of the IMF's financial soundness indicator is the rival (rule 38).
    Candidate(
        id="CAND_FRED_CPP_US",
        country="US",
        concept="commercial_property_prices",
        source="fred",
        producer="bloc",
        area="US",
        serves="BIS_CPP_US",
        flow="",
        key="COMREPUSQ159N",
        months=3,
    ),
)
CANDIDATE_BY_ID = {c.id: c for c in CANDIDATES}
