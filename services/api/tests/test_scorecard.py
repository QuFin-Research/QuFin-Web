"""The scorecard correction mechanism: late or missing data lowers confidence, never the score.

These tests are the enforcement of the rule in services/api/CLAUDE.md. Do not loosen them to
make a change pass; if one fails, the change has reintroduced a directional bias.
"""

import random
from datetime import UTC, date, datetime, timedelta

import pytest

from app.data import scorecard_catalog
from app.data.scorecard_catalog import ScoreSpec
from app.domain.scorecard import (
    IndicatorScore,
    build_scorecard,
    combine_pillar,
    history_score,
    pair_confidence,
    rescaled_average,
    score_indicator,
    to_monthly,
    transform,
)
from app.jobs import scorecard as scorecard_job
from app.jobs.scorecard import MAX_MEAN_BIAS, bias_backtest
from app.stores.macro import OPEN_END, MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)


def ind(score, weight=1.0, importance=1.0, pillar="growth", id="X"):
    return IndicatorScore(id, pillar, date(2026, 9, 1), 0.0, score, importance, weight)


def naive_sum(indicators):
    """The biased alternative: missing counted as zero over the full weight."""
    full = sum(i.importance for i in indicators)
    return sum((i.score or 0.0) * i.weight for i in indicators) / full


# --- the rule -------------------------------------------------------------------------------


@pytest.mark.parametrize("level", [2.0, -2.0])
def test_a_missing_indicator_does_not_pull_the_score_toward_neutral(level):
    fresh = [ind(level), ind(level), ind(level)]
    one_missing = [ind(level), ind(level), ind(level, weight=0.0)]
    pillar = combine_pillar("growth", one_missing)
    assert pillar.score == pytest.approx(level)  # the view is unchanged...
    assert pillar.confidence == pytest.approx(2 / 3)  # ...only the certainty drops
    assert combine_pillar("growth", fresh).confidence == 1.0
    # The plain sum would underrate a strong economy and overrate a weak one.
    assert abs(naive_sum(one_missing)) < abs(level)


def test_a_late_indicator_counts_for_less_but_cannot_push_the_score_alone():
    rng = random.Random(7)  # noqa: S311  (reproducible test data)
    for _ in range(500):
        inds = [ind(rng.uniform(-3, 3), weight=rng.choice([0.0, rng.random()])) for _ in range(5)]
        used = [i.score for i in inds if i.weight > 0]
        score = combine_pillar("growth", inds).score
        if not used:
            assert score is None
            continue
        # A weighted average never leaves the range of the indicators it averages.
        assert min(used) - 1e-9 <= score <= max(used) + 1e-9


def test_uniform_lateness_changes_confidence_not_the_score():
    scores = [1.5, -0.5, 2.0]
    fresh = combine_pillar("growth", [ind(s, weight=1.0) for s in scores])
    late = combine_pillar("growth", [ind(s, weight=0.4) for s in scores])
    assert late.score == pytest.approx(fresh.score)
    assert late.confidence == pytest.approx(0.4)


def test_unscorable_indicators_drop_out_and_lower_confidence():
    pillar = combine_pillar("growth", [ind(1.0), ind(None, weight=0.0)])
    assert pillar.score == 1.0
    assert pillar.confidence == 0.5
    assert combine_pillar("growth", [ind(None, weight=0.0)]).score is None


def test_overall_weights_pillars_by_confidence_and_rescales():
    card = build_scorecard(
        [ind(2.0, pillar="growth"), ind(-1.0, pillar="labour", weight=0.5)]
        + [ind(None, weight=0.0, pillar=p) for p in ("inflation", "policy", "sentiment")]
    )
    assert card.overall == pytest.approx((2.0 * 1.0 + -1.0 * 0.5) / 1.5)
    assert card.overall_confidence == pytest.approx((1.0 + 0.5) / 5)


def test_a_pair_is_only_as_certain_as_its_less_certain_side():
    assert pair_confidence(0.9, 0.55) == 0.55
    assert rescaled_average([]) is None


# --- scoring one indicator --------------------------------------------------------------------


def monthly_points(values, start=date(2014, 1, 1)):
    out, y, m = [], start.year, start.month
    for v in values:
        out.append((date(y, m, 1), v))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_history_score_is_a_clipped_z_score_and_needs_three_years():
    assert history_score(monthly_points([1.0] * 30 + [2.0]), "Monthly") is None
    flat_then_jump = monthly_points([0.0, 1.0] * 30 + [100.0])
    assert history_score(flat_then_jump, "Monthly") == 3.0
    assert history_score(monthly_points([5.0] * 40), "Monthly") == 0.0


def test_polarity_flips_indicators_where_higher_is_weaker():
    points = monthly_points([float(i % 7) for i in range(60)] + [10.0])
    up = score_indicator("X", "labour", ScoreSpec("level"), "Monthly", points, 1.0)
    down = score_indicator("X", "labour", ScoreSpec("level", -1), "Monthly", points, 1.0)
    assert up.score > 0
    assert down.score == pytest.approx(-up.score)


def test_daily_data_is_averaged_by_month_and_yoy_needs_a_year_earlier():
    daily = [(date(2026, 1, d), float(d)) for d in (2, 3)] + [(date(2026, 2, 2), None)]
    assert to_monthly(daily, "Daily") == [(date(2026, 1, 1), 2.5)]
    yoy = transform([(date(2025, 3, 1), 100.0), (date(2026, 3, 1), 103.0)], "yoy")
    assert yoy == [(date(2026, 3, 1), pytest.approx(3.0))]


# --- live scorecard through the API -----------------------------------------------------------


def test_api_serves_live_scorecard_with_confidence_and_pending(client, ingested):  # noqa: F811
    [us] = client.get("/v1/scorecards/countries", params={"asOf": "2026-10-10"}).json()
    assert us["data"] == "live"
    assert us["code"] == "US"
    assert set(us["confidence"]) == {"growth", "inflation", "labour", "policy", "sentiment"}
    # Two months of unemployment are too little history to score, so there is no evidence:
    # scores sit at 0 with 0% confidence, and every missing series is listed as pending.
    assert us["overallConfidence"] == 0.0
    assert any(p["reason"] == "Not ingested" for p in us["pending"])
    assert {i["id"] for i in us["indicators"]} == set(scorecard_catalog.SCORED)


# --- the required bias backtest -----------------------------------------------------------------


def _store_series(store, series_id, title, values, release_lag, skip=frozenset()):
    vintages = [
        Vintage(period, period + timedelta(days=release_lag), OPEN_END, value)
        for period, value in values
        if period not in skip
    ]
    meta = SeriesMeta(
        id=series_id,
        source="fred",
        title=title,
        units="Index",
        frequency="Monthly",
        seasonal_adjustment="SA",
        country="US",
        dimension="labour",
        last_updated=datetime(2020, 1, 1, tzinfo=UTC),
        source_name="Test agency",
    )
    store.replace_series(meta, vintages)


def test_bias_backtest_finds_no_bias_where_a_plain_sum_would(db_session, monkeypatch):  # noqa: F811
    # Two labour indicators tracking the same improving labour market. One goes
    # missing for whole stretches (a delayed or suspended release): the rescaled scorecard
    # keeps the view, the plain sum would have underrated the economy.
    monkeypatch.setattr(
        scorecard_job,
        "SCORED",
        {"AWHMAN": ScoreSpec("level"), "PAYEMS": ScoreSpec("level")},
    )
    rng = random.Random(3)  # noqa: S311  (reproducible test data)
    trend = [0.0004 * i**2 + rng.gauss(0, 0.2) for i in range(144)]  # accelerating
    values = monthly_points(trend, start=date(2008, 1, 1))
    gaps = {p for p, _ in values if p.year in (2015, 2016, 2017, 2018) and p.month >= 3}
    store = MacroStore(db_session)
    _store_series(store, "AWHMAN", "Hours", values, release_lag=5)
    _store_series(store, "PAYEMS", "Payrolls", values, release_lag=5, skip=gaps)

    report = bias_backtest(db_session, date(2014, 1, 1), date(2019, 6, 1))
    labour = next(p for p in report.pillars if p.pillar == "labour")
    assert labour.observations > 50
    assert abs(labour.mean_difference) <= MAX_MEAN_BIAS
    assert labour.naive_mean_difference < -MAX_MEAN_BIAS  # what the rescaling prevents
    assert report.passed


def test_growth_is_scored_in_real_terms_only():
    # Nominal dollar series grow with prices; scoring them would read inflation as growth.
    nominal = {"RSAFS", "PI", "NEWORDER", "ACOGNO"}
    assert not nominal & set(scorecard_catalog.SCORED)
    assert {"GDPC1", "RRSFS", "W875RX1"} <= set(scorecard_catalog.SCORED)
