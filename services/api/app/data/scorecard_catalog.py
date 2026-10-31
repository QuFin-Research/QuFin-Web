"""How each macro series feeds the country scorecard.

A pillar score says how strong that pillar is running, from -3 (very weak) to +3 (very
strong): growth strong, inflation hot, labour market tight, policy tight, sentiment upbeat.
Each of those supports the currency, so the overall score reads as macro support for it.

Every indicator is scored against its own history (see app.domain.scorecard). `polarity` is
-1 where a higher reading means a weaker pillar, e.g. unemployment for labour or wider credit
spreads for sentiment. `transform` is "level" for rates, indexes and surveys, "yoy" (percent
change over a year) for quantities and prices. `importance` is the base weight before the
timeliness weight; all start equal until a reviewed reason says otherwise.

Series in the macro catalog but not here are stored and shown, but not scored (their meaning
for a pillar is ambiguous or duplicated, e.g. the prime rate tracks fed funds one for one).
"""

from dataclasses import dataclass
from typing import Literal

Transform = Literal["level", "yoy"]


@dataclass(frozen=True)
class ScoreSpec:
    transform: Transform
    polarity: Literal[1, -1] = 1
    importance: float = 1.0


SCORED: dict[str, ScoreSpec] = {
    # Growth
    "GDPC1": ScoreSpec("yoy"),
    "INDPRO": ScoreSpec("yoy"),
    "RSAFS": ScoreSpec("yoy"),
    "PI": ScoreSpec("yoy"),
    "NEWORDER": ScoreSpec("yoy"),
    "PERMIT": ScoreSpec("yoy"),
    "NOCDFSA066MSFRBPHI": ScoreSpec("level"),
    # Inflation
    "CPIAUCSL": ScoreSpec("yoy"),
    "CPILFESL": ScoreSpec("yoy"),
    "PCEPILFE": ScoreSpec("yoy"),
    "CUSR0000SAS": ScoreSpec("yoy"),
    "T10YIE": ScoreSpec("level"),
    # Labour
    "UNRATE": ScoreSpec("level", -1),
    "PAYEMS": ScoreSpec("yoy"),
    "ICSA": ScoreSpec("level", -1),
    "AWHMAN": ScoreSpec("level"),
    "UEMPMEAN": ScoreSpec("level", -1),
    # Policy (tight = strong)
    "FEDFUNDS": ScoreSpec("level"),
    "DGS2": ScoreSpec("level"),
    "DFII10": ScoreSpec("level"),
    "T10Y3M": ScoreSpec("level", -1),  # an inverted curve means tight policy
    "M2SL": ScoreSpec("yoy", -1),
    "WALCL": ScoreSpec("yoy", -1),  # a shrinking Fed balance sheet is tightening
    # Sentiment and financial conditions
    "UMCSENT": ScoreSpec("level"),
    "NFCI": ScoreSpec("level", -1),  # higher NFCI = tighter financial conditions
    "BAA10Y": ScoreSpec("level", -1),
}
