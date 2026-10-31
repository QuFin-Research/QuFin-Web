"""Build country scorecards from the point-in-time macro store, and test them for bias."""

import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data.macro_catalog import BY_ID
from app.data.scorecard_catalog import SCORED
from app.domain.freshness import STEP_DAYS, frequency_code
from app.domain.scorecard import (
    PILLARS,
    IndicatorScore,
    Scorecard,
    build_scorecard,
    rescaled_average,
    score_indicator,
)
from app.jobs.check_data import LAG_WINDOW, SeriesStatus, macro_status
from app.schemas.market import (
    CountryScore,
    CountryScores,
    PillarConfidence,
    ScorecardIndicator,
)
from app.schemas.market import PendingRelease as PendingReleaseOut
from app.stores.macro import MacroStore

# Ten years of z-score history plus a year for the year-over-year change.
LOOKBACK = timedelta(days=366 * 11 + 31)
# Releases due this soon are listed as pending, so users know the score may move.
PENDING_HORIZON = timedelta(days=14)


@dataclass(frozen=True)
class IndicatorStatus:
    score: IndicatorScore
    status: SeriesStatus | None  # None when the series was never ingested
    title: str
    source_name: str | None
    frequency: str = ""
    last_period: date | None = None  # latest period of the raw series known on the date


@dataclass(frozen=True)
class PendingRelease:
    series_id: str
    title: str
    source_name: str | None
    period: date | None  # the period expected next
    source_release: date | None  # when the source should publish (or did)
    fred_release: date | None  # when FRED should show it
    reason: str


@dataclass(frozen=True)
class CountryScorecard:
    country: str
    as_of: date
    scorecard: Scorecard
    indicators: tuple[IndicatorStatus, ...]
    pending: tuple[PendingRelease, ...]


def _next_period(period: date, frequency: str) -> date:
    months = 3 if frequency_code(frequency) == "Q" else 1
    if frequency_code(frequency) in ("D", "W", "B"):
        return period + timedelta(days=STEP_DAYS[frequency_code(frequency)])
    y, m = divmod(period.month - 1 + months, 12)
    return date(period.year + y, m + 1, 1)


def indicator_statuses(
    store: MacroStore,
    as_of: date,
    *,
    period_end: date | None = None,
    full_weights: bool = False,
) -> list[IndicatorStatus]:
    """Every scored indicator as it was known on `as_of`.

    `period_end` cuts off later periods and `full_weights` ignores timeliness; both exist only
    for the bias backtest's complete-information baseline.
    """
    result = []
    for series_id, spec in SCORED.items():
        entry = BY_ID[series_id]
        meta = store.get_series(series_id)
        if meta is None:
            empty = IndicatorScore(
                series_id, entry.dimension, None, None, None, spec.importance, 0.0
            )
            result.append(IndicatorStatus(empty, None, series_id, None))
            continue
        observations = store.as_of(series_id, as_of, start=as_of - LOOKBACK, end=period_end)
        points = [(o.period, o.value) for o in observations]
        releases = {
            period: released
            for period, released in store.first_releases(as_of - LAG_WINDOW, series_id)
            .get(series_id, {})
            .items()
            if released <= as_of
        }
        last_period = observations[-1].period if observations else None
        status = macro_status(meta, last_period, releases, as_of)
        weight = 1.0 if full_weights else status.timeliness.weight
        score = score_indicator(series_id, entry.dimension, spec, meta.frequency, points, weight)
        result.append(
            IndicatorStatus(
                score, status, meta.title, meta.source_name, meta.frequency, last_period
            )
        )
    return result


def pending_releases(statuses: list[IndicatorStatus], as_of: date) -> list[PendingRelease]:
    pending = []
    for s in statuses:
        if s.status is None:
            pending.append(
                PendingRelease(s.score.id, s.title, None, None, None, None, "Not ingested")
            )
            continue
        f = s.status.freshness
        delay = s.status.timeliness.fred_delay_days
        if not f.usable:
            pending.append(
                PendingRelease(s.score.id, s.title, s.source_name, None, None, None, f.reason)
            )
            continue
        # Daily rates are due every business day; listing them would bury the releases that
        # actually move a pillar.
        if f.next_due is None or frequency_code(s.frequency) == "D":
            continue
        source_due = f.next_due - timedelta(days=delay)
        awaiting_fred = delay > 0 and source_due <= as_of
        if not awaiting_fred and f.next_due > as_of + PENDING_HORIZON:
            continue
        period = _next_period(s.last_period, s.frequency) if s.last_period else None
        reason = "Published by the source, not yet on FRED" if awaiting_fred else "Next release due"
        pending.append(
            PendingRelease(
                s.score.id, s.title, s.source_name, period, source_due, f.next_due, reason
            )
        )
    return sorted(pending, key=lambda p: p.fred_release or date.max)


def us_scorecard(session: Session, as_of: date) -> CountryScorecard | None:
    """The live US scorecard as known on `as_of`; None when no macro data is stored."""
    store = MacroStore(session)
    if not store.list_series():
        return None
    statuses = indicator_statuses(store, as_of)
    card = build_scorecard([s.score for s in statuses])
    return CountryScorecard(
        "US", as_of, card, tuple(statuses), tuple(pending_releases(statuses, as_of))
    )


def to_country_score(card: CountryScorecard) -> CountryScore:
    pillars = card.scorecard.pillars
    return CountryScore(
        code="US",
        country="United States",
        currency="USD",
        # A pillar with no usable indicator shows 0 at 0% confidence: no evidence either way.
        scores=CountryScores(
            **{p: round(ps.score, 2) if ps.score is not None else 0.0 for p, ps in pillars.items()}
        ),
        overall=round(card.scorecard.overall or 0.0, 2),
        data="live",
        confidence=PillarConfidence(**{p: round(ps.confidence, 2) for p, ps in pillars.items()}),
        overall_confidence=round(card.scorecard.overall_confidence, 2),
        as_of=card.as_of,
        indicators=[
            ScorecardIndicator(
                id=i.score.id,
                title=i.title,
                pillar=i.score.pillar,
                source_name=i.source_name,
                period=i.score.period,
                value=None if i.score.value is None else round(i.score.value, 3),
                score=None if i.score.score is None else round(i.score.score, 2),
                weight=round(i.score.weight, 2),
                usable=i.status is not None and i.status.freshness.usable,
                status=i.status.freshness.status if i.status else "missing",
            )
            for i in card.indicators
        ],
        pending=[
            PendingReleaseOut(
                series_id=p.series_id,
                title=p.title,
                source_name=p.source_name,
                period=p.period,
                source_release=p.source_release,
                fred_release=p.fred_release,
                reason=p.reason,
            )
            for p in card.pending
        ],
    )


# --- bias backtest -------------------------------------------------------------------------

# Average gap between what users saw and the complete-information score that the scheme may
# show before it counts as biased. Scores run -3..+3.
MAX_MEAN_BIAS = 0.25
# Revisions and late releases for a period are mostly in by then.
COMPLETE_AFTER = timedelta(days=120)


@dataclass(frozen=True)
class PillarBias:
    pillar: str
    observations: int
    mean_difference: float  # seen minus complete; ~0 means no directional bias
    mean_abs_difference: float  # how much the delays cost in precision
    naive_mean_difference: float  # the same for a plain sum with missing counted as 0

    @property
    def passed(self) -> bool:
        return abs(self.mean_difference) <= MAX_MEAN_BIAS


@dataclass(frozen=True)
class BiasReport:
    start: date
    end: date
    pillars: tuple[PillarBias, ...]

    @property
    def passed(self) -> bool:
        return all(p.passed for p in self.pillars)


def _naive(statuses: list[IndicatorStatus]) -> dict[str, float | None]:
    """The biased alternative, kept only to show what the rescaling protects against."""
    result: dict[str, float | None] = {}
    for pillar in PILLARS:
        inds = [s.score for s in statuses if s.score.pillar == pillar]
        full = sum(i.importance for i in inds)
        total = sum((i.score or 0.0) * i.weight for i in inds)
        result[pillar] = total / full if full else None
    return result


def bias_backtest(session: Session, start: date, end: date) -> BiasReport:
    """Compare the scorecard users would have seen each month with complete information.

    Seen: as published on the first of each month, with timeliness weights and missing data.
    Complete: the same periods (everything before that date), read COMPLETE_AFTER later when
    late releases have arrived, at full weight. Their mean difference must be about zero.
    """
    store = MacroStore(session)
    diffs: dict[str, list[float]] = {p: [] for p in (*PILLARS, "overall")}
    naive: dict[str, list[float]] = {p: [] for p in (*PILLARS, "overall")}
    month = date(start.year, start.month, 1)
    while month <= end:
        seen_statuses = indicator_statuses(store, month)
        seen = build_scorecard([s.score for s in seen_statuses])
        complete = build_scorecard(
            [
                s.score
                for s in indicator_statuses(
                    store,
                    month + COMPLETE_AFTER,
                    period_end=month - timedelta(days=1),
                    full_weights=True,
                )
            ]
        )
        seen_naive = _naive(seen_statuses)
        for pillar in PILLARS:
            a, b = seen.pillars[pillar].score, complete.pillars[pillar].score
            if a is not None and b is not None:
                diffs[pillar].append(a - b)
            if seen_naive[pillar] is not None and b is not None:
                naive[pillar].append(seen_naive[pillar] - b)
        if seen.overall is not None and complete.overall is not None:
            diffs["overall"].append(seen.overall - complete.overall)
            naive_overall = rescaled_average(
                [(v, 1.0) for v in seen_naive.values() if v is not None]
            )
            if naive_overall is not None:
                naive["overall"].append(naive_overall - complete.overall)
        y, m = divmod(month.month, 12)
        month = date(month.year + y, m + 1, 1)
    return BiasReport(
        start,
        end,
        tuple(
            PillarBias(
                p,
                len(diffs[p]),
                statistics.fmean(diffs[p]) if diffs[p] else 0.0,
                statistics.fmean(abs(d) for d in diffs[p]) if diffs[p] else 0.0,
                statistics.fmean(naive[p]) if naive[p] else 0.0,
            )
            for p in diffs
        ),
    )


def format_bias_report(report: BiasReport) -> str:
    lines = [
        f"Scorecard bias backtest {report.start} to {report.end} "
        f"(pass: |mean difference| <= {MAX_MEAN_BIAS})",
        f"{'pillar':<10} {'months':>6} {'mean diff':>10} {'mean |diff|':>12} "
        f"{'naive diff':>11}  result",
    ]
    for p in report.pillars:
        lines.append(
            f"{p.pillar:<10} {p.observations:>6} {p.mean_difference:>+10.3f} "
            f"{p.mean_abs_difference:>12.3f} {p.naive_mean_difference:>+11.3f}  "
            f"{'PASS' if p.passed else 'FAIL'}"
        )
    lines.append("PASSED" if report.passed else "FAILED: the scorecard is biased; do not use it")
    return "\n".join(lines)
