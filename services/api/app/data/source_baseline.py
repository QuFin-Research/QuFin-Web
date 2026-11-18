"""Source decisions made before the store existed, recorded once (rules 16, P).

`uv run python -m app.cli source-decision --baseline` applies them; a pair that already has any
decision is left alone, so running it twice changes nothing. Decisions made from now on are
recorded with `source-decision` at the time and are not listed here.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BaselineDecision:
    country: str
    concept: str
    series_id: str
    source: str
    effective_from: date
    status: str
    reason: str


BASELINE: tuple[BaselineDecision, ...] = (
    BaselineDecision(
        "PT",
        "consumer_prices",
        "CP0000PTM086NEST",
        "fred",
        date(2026, 11, 18),
        "provisional",
        "Moved from the IMF (IMF_CPI_PRT, overdue: the IMF had no data after July 2026) to FRED's "
        "copy of Eurostat's HICP, then chosen as FRED first. Provisional under rule P: Eurostat "
        "itself held October on 4 Nov 2026 while FRED stopped at September, so Eurostat is "
        "expected to win once its connector exists (assumptions register 4p). The IMF series was "
        "deleted when it was replaced, so there is no retired series to keep.",
    ),
)
