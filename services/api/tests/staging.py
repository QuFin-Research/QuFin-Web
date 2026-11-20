"""A sample candidate for the staging tests.

The registry (`app/data/candidates.py`) is empty since rule 38's Bloc aggregator first, so the
staging, measurement and promotion tests build their own candidate: the IMF's consumer prices of
Germany, timed against the Eurostat series that serves the pair.
"""

from app.data.candidates import CANDIDATE_BY_ID, Candidate
from app.data.macro_ids import IMF_CPI_FLOW, IMF_CPI_KEY

DE = Candidate(
    id="CAND_IMF_CPI_DEU",
    country="DE",
    concept="consumer_prices",
    source="imf",
    producer="global",
    area="DEU",
    serves="ESTAT_HICP_DE",
    flow=IMF_CPI_FLOW,
    key=IMF_CPI_KEY.format(area="DEU"),
)


def register(monkeypatch, *candidates: Candidate) -> None:
    """Name the candidates in the registry for the length of a test."""
    for c in candidates:
        monkeypatch.setitem(CANDIDATE_BY_ID, c.id, c)
