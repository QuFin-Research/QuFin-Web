"""Country scorecard: unbiased pillar scores, with confidence reported separately.

QuFin rule (see RULEBOOK.md). A late or missing indicator must make a score less
certain, never more bullish or bearish:

- Each indicator is scored against its own history as published at the time, on two parts:
  where it stands (its level, or its change over a year for quantities) and how fast it is
  moving (its change over three months: annualised percent for quantities, points for rates).
  Each part is a z-score over the trailing ten years, clipped to -3..+3 and flipped where a
  higher reading means a weaker pillar; the indicator's score is their weighted average
  (MOMENTUM_WEIGHT), rescaled when one part is missing. Daily and weekly series enter as
  monthly averages that already include the latest week, so they lead the monthly releases.
- A pillar is the weighted average of the indicators that are usable, with the weights
  rescaled to sum to one: score = sum(w * s) / sum(w). An overdue, discontinued or missing
  indicator drops out (weight 0); it is never counted as a zero, which would pull every score
  toward neutral (underrating strong economies and overrating weak ones).
- w is the indicator's base importance times its timeliness weight, so late data counts for
  less within the pillar, but cannot move the score on its own.
- Confidence = sum(w) / sum(base importance): how much fresh evidence stands behind the score.
  Caution belongs in position size, not in the score.
- Overall = the pillar scores averaged with their confidences as weights, rescaled the same
  way; a pair of currencies is only as certain as its less certain side.
"""

import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.data.macro_catalog import ChangeKind
from app.data.scorecard_catalog import ScoreSpec, Transform
from app.domain.freshness import frequency_code

PILLARS = ("growth", "inflation", "labour", "policy", "sentiment")
SCORE_LIMIT = 3.0
# Part 0, section 0.2 (S1): the lookback window and the fewest usable observations a z-score needs.
# Fewer points than the floor and the history says too little about what is normal.
ZSCORE_WINDOW_YEARS_STANDARD = 10  # monthly or faster, quarterly and semi-annual series
ZSCORE_WINDOW_YEARS_ANNUAL = 20  # an annual series needs a longer history for the same sample
ZSCORE_MIN_OBSERVATIONS_MONTHLY = 36
ZSCORE_MIN_OBSERVATIONS_QUARTERLY = 16
ZSCORE_MIN_OBSERVATIONS_SEMIANNUAL = 8
ZSCORE_MIN_OBSERVATIONS_ANNUAL = 8
HISTORY_YEARS = ZSCORE_WINDOW_YEARS_STANDARD  # the methodology page reports this one
MIN_OBSERVATIONS = {
    "M": ZSCORE_MIN_OBSERVATIONS_MONTHLY,
    "Q": ZSCORE_MIN_OBSERVATIONS_QUARTERLY,
    "S": ZSCORE_MIN_OBSERVATIONS_SEMIANNUAL,
    "A": ZSCORE_MIN_OBSERVATIONS_ANNUAL,
}
PERIODS_PER_YEAR = {"M": 12, "Q": 4, "S": 2, "A": 1}
# Momentum looks one native step back: three months, one quarter, one half year, one year (S1).
MOMENTUM_MONTHS = {"M": 3, "Q": 3, "S": 6, "A": 12}
# Share of an indicator's score that comes from its recent momentum rather than its standing.
MOMENTUM_WEIGHT = 0.5


@dataclass(frozen=True)
class IndicatorScore:
    id: str
    pillar: str
    period: date | None
    value: float | None  # after the transform (level, or % change over a year)
    score: float | None  # -3..+3, None when there is too little history
    importance: float
    weight: float  # importance x timeliness weight; 0 when not usable or not scored
    level_score: float | None = None  # where it stands
    momentum_score: float | None = None  # how fast it is moving (3-month change)


@dataclass(frozen=True)
class PillarScore:
    pillar: str
    score: float | None  # None when no usable indicator
    confidence: float  # 0..1
    indicators: tuple[IndicatorScore, ...]


@dataclass(frozen=True)
class Scorecard:
    pillars: dict[str, PillarScore]
    overall: float | None
    overall_confidence: float


def to_monthly(
    points: Sequence[tuple[date, float | None]], frequency: str
) -> list[tuple[date, float]]:
    """Daily and weekly data averaged by calendar month; monthly and quarterly kept as is."""
    code = frequency_code(frequency)
    values = [(p, v) for p, v in points if v is not None]
    if code in ("M", "Q", "S", "A"):
        return values
    months: dict[date, list[float]] = defaultdict(list)
    for p, v in values:
        months[p.replace(day=1)].append(v)
    return [(m, statistics.fmean(vs)) for m, vs in sorted(months.items())]


def transform(points: Sequence[tuple[date, float]], kind: Transform) -> list[tuple[date, float]]:
    if kind == "level":
        return list(points)
    by_period = dict(points)
    result = []
    for p, v in points:
        prior = by_period.get(p.replace(year=p.year - 1))
        if prior:
            result.append((p, (v / prior - 1) * 100))
    return result


def scoring_grid(frequency: str) -> str:
    """M, Q, S or A: daily and weekly data are averaged to months before they are scored."""
    code = frequency_code(frequency)
    return code if code in ("Q", "S", "A") else "M"


def history_score(points: Sequence[tuple[date, float]], frequency: str) -> float | None:
    """The latest value as a z-score over the lookback window, clipped to -3..+3 (S1)."""
    grid = scoring_grid(frequency)
    years = ZSCORE_WINDOW_YEARS_ANNUAL if grid == "A" else ZSCORE_WINDOW_YEARS_STANDARD
    window = [v for _, v in points[-(years * PERIODS_PER_YEAR[grid]) :]]
    if len(window) < MIN_OBSERVATIONS[grid]:
        return None
    sd = statistics.pstdev(window)
    if sd == 0:
        return 0.0
    z = (window[-1] - statistics.fmean(window)) / sd
    return max(-SCORE_LIMIT, min(SCORE_LIMIT, z))


def momentum(
    points: Sequence[tuple[date, float]], frequency: str, change: ChangeKind
) -> list[tuple[date, float]]:
    """Each period's change over one native step: three months, one quarter, one half year or one
    year (S1). A percent change is annualised; a change in points or own units is the difference."""
    months = MOMENTUM_MONTHS[scoring_grid(frequency)]
    by_period = dict(points)
    result = []
    for p, v in points:
        y, m = divmod(p.month - 1 - months, 12)
        prior = by_period.get(date(p.year + y, m + 1, 1))
        if prior is None:
            continue
        if change == "diff":
            result.append((p, v - prior))
        elif prior > 0 and v > 0:
            result.append((p, ((v / prior) ** (12 // months) - 1) * 100))  # annualised
    return result


def score_indicator(
    series_id: str,
    pillar: str,
    spec: ScoreSpec,
    frequency: str,
    observations: Sequence[tuple[date, float | None]],
    timeliness_weight: float,
    change: ChangeKind = "pct",
) -> IndicatorScore:
    monthly = to_monthly(observations, frequency)
    transformed = transform(monthly, spec.transform)
    level = history_score(transformed, frequency) if transformed else None
    moving = momentum(monthly, frequency, change)
    pace = history_score(moving, frequency) if moving else None
    level = None if level is None else level * spec.polarity
    pace = None if pace is None else pace * spec.polarity
    score = rescaled_average(
        [
            (s, w)
            for s, w in ((level, 1 - MOMENTUM_WEIGHT), (pace, MOMENTUM_WEIGHT))
            if s is not None
        ]
    )
    period = transformed[-1][0] if transformed else None
    value = transformed[-1][1] if transformed else None
    weight = spec.importance * timeliness_weight if score is not None else 0.0
    return IndicatorScore(
        series_id, pillar, period, value, score, spec.importance, weight, level, pace
    )


def rescaled_average(pairs: Sequence[tuple[float, float]]) -> float | None:
    """sum(w * s) / sum(w) over (score, weight) pairs with positive weight; None if none."""
    used = [(s, w) for s, w in pairs if w > 0]
    total = sum(w for _, w in used)
    return sum(s * w for s, w in used) / total if total else None


def combine_pillar(pillar: str, indicators: Sequence[IndicatorScore]) -> PillarScore:
    full = sum(i.importance for i in indicators)
    pairs = [(i.score, i.weight) for i in indicators if i.score is not None]
    score = rescaled_average(pairs)
    confidence = sum(w for _, w in pairs) / full if full else 0.0
    return PillarScore(pillar, score, confidence, tuple(indicators))


def build_scorecard(indicators: Sequence[IndicatorScore]) -> Scorecard:
    by_pillar = {p: [i for i in indicators if i.pillar == p] for p in PILLARS}
    pillars = {p: combine_pillar(p, inds) for p, inds in by_pillar.items()}
    overall = rescaled_average(
        [(ps.score, ps.confidence) for ps in pillars.values() if ps.score is not None]
    )
    confidence = statistics.fmean(ps.confidence for ps in pillars.values())
    return Scorecard(pillars, overall, confidence)


def pair_confidence(base: float, quote: float) -> float:
    """A currency pair is only as certain as its less certain side."""
    return min(base, quote)


def size_factor(confidence: float) -> float:
    """The share of a normal position a trade idea may take (S4): caution goes into the size,
    never into the view. Full confidence is a full position, none is no position; the score
    itself is not touched. For a pair, pass `pair_confidence` (S8)."""
    return max(0.0, min(1.0, confidence))
