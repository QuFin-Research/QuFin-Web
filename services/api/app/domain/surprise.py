"""Surprise of a release: how far the first print landed from what the market expected.

`surprise = actual - consensus`, standardised by the spread of that series' own past surprises, so
a 0.1 point miss on a quiet series scores higher than on a noisy one. It needs a consensus and
enough history; without them the score is empty, never estimated (rule 8).
"""

import statistics
from collections.abc import Sequence

# Past surprises needed before a standard deviation means anything.
MIN_HISTORY = 8


def surprise(actual: float | None, consensus: float | None) -> float | None:
    if actual is None or consensus is None:
        return None
    return actual - consensus


def surprise_score(
    actual: float | None, consensus: float | None, history: Sequence[float]
) -> float | None:
    """(actual - consensus) / stdev(past surprises); None when it cannot be stated honestly."""
    raw = surprise(actual, consensus)
    if raw is None or len(history) < MIN_HISTORY:
        return None
    spread = statistics.pstdev(history)
    if spread == 0:
        return None
    return raw / spread
