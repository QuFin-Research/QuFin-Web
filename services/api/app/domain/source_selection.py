"""Which source serves a country-indicator pair (rule 38), as a pure function.

Rule 38 says the same input always yields the same choice. This is that choice, in the order the
rule gives:

1. Eligibility: an ineligible candidate is never chosen, however early it is.
2. Earliest, then frequency: the source whose new observations can first be read wins; where two
   are equally early the one that releases more often wins.
3. Ties: the most native source (Part 0: the original producer, then the aggregator of the
   economy's own country or bloc, then a global aggregator); then the fresher latest period at the
   probe recorded for the decision; then the source code in ascending order. Load order never
   matters.

A new pair has no measured lag yet: it is served from the candidate with the most recent period at
the probe, then by frequency, then by nativeness (the provisional decision of rule 38, "New pairs").

The function chooses; it does not measure. Lags and probes come from the register (rule 12).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Literal

Producer = Literal["original", "bloc", "global"]

# Fastest first (rule 38 (b)).
FREQUENCY_ORDER = ("hourly", "daily", "weekly", "monthly", "quarterly", "semi-annual", "annual")
NATIVE_ORDER: dict[Producer, int] = {"original": 0, "bloc": 1, "global": 2}


@dataclass(frozen=True)
class Candidate:
    source: str  # the source code, e.g. "eurostat"
    eligible: bool  # licence, access, verified definition and live schedule (rule 38)
    frequency: str  # one of FREQUENCY_ORDER
    producer: Producer  # how native it is for this economy (Part 0)
    lag_days: int | None = None  # whole days from period end to first read; None: not measured
    latest_period: date | None = None  # at the probe recorded for the decision


def _freshness(candidate: Candidate) -> int:
    """Later periods sort first; a candidate with no period sorts last."""
    return -candidate.latest_period.toordinal() if candidate.latest_period else 0


def choose(candidates: Iterable[Candidate]) -> Candidate | None:
    """The source rule 38 picks, or None when no candidate is eligible."""
    eligible = [c for c in candidates if c.eligible]
    if not eligible:
        return None
    unknown = [c.source for c in eligible if c.frequency not in FREQUENCY_ORDER]
    if unknown:
        raise ValueError(f"unknown frequency for {', '.join(sorted(unknown))}")
    measured = all(c.lag_days is not None for c in eligible)

    def key(c: Candidate) -> tuple:
        freq = FREQUENCY_ORDER.index(c.frequency)
        native = NATIVE_ORDER[c.producer]
        if measured:
            return (c.lag_days, freq, native, _freshness(c), c.source)
        return (_freshness(c), freq, native, c.source)

    return min(eligible, key=key)
