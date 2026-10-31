"""Change measures, momentum and the guard against changing a series that is already a change."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.macro_catalog import BY_ID, CATALOG
from app.data.scorecard_catalog import SCORED, ScoreSpec
from app.domain.changes import change_measures
from app.domain.scorecard import momentum, score_indicator
from app.jobs.check_data import double_change_reason
from app.stores.macro import SeriesMeta


def monthly(values, start=date(2020, 1, 1)):
    out, y, m = [], start.year, start.month
    for v in values:
        out.append((date(y, m, 1), v))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def meta(series_id, units):
    return SeriesMeta(
        series_id,
        "fred",
        "T",
        units,
        "Monthly",
        "SA",
        "US",
        "growth",
        datetime(2026, 1, 1, tzinfo=UTC),
    )


# --- no change of a change --------------------------------------------------------------------


def test_series_published_as_a_change_are_never_changed_again():
    for entry in CATALOG:
        spec = SCORED.get(entry.id)
        if entry.published_as_change:
            assert entry.change == "diff", entry.id
            assert spec is None or spec.transform == "level", entry.id
        if spec is not None and spec.transform == "yoy":
            assert entry.change == "pct", entry.id  # a y/y on a rate or spread misleads


def test_wei_is_declared_a_growth_rate_although_its_units_say_index():
    # FRED lists WEI's units as "Index", but it is scaled to four-quarter GDP growth.
    assert BY_ID["WEI"].published_as_change
    assert double_change_reason(meta("WEI", "Index"), BY_ID["WEI"]) is None  # scored as published


def test_check_flags_a_percent_change_of_a_series_published_as_a_change():
    entry = BY_ID["PAYEMS"]  # configured as a percent-change quantity
    reason = double_change_reason(meta("PAYEMS", "Percent Change from Year Ago"), entry)
    assert reason and "change of a change" in reason
    assert double_change_reason(meta("PAYEMS", "Thousands of Persons"), entry) is None


# --- change measures -----------------------------------------------------------------------


def test_quantities_change_in_percent_and_rates_in_points():
    levels = monthly([100.0 + i for i in range(13)])
    pct = {c.horizon: c for c in change_measures(levels, "Monthly", "pct")}
    assert pct["1m"].value == pytest.approx(100 * (112 / 111 - 1), abs=1e-3)
    assert pct["1m"].unit == "%"
    assert pct["3m"].unit == "% ann."
    assert pct["1y"].value == pytest.approx(12.0)
    rate = monthly([4.0, 4.1, 4.2, 4.4])
    pts = {c.horizon: c for c in change_measures(rate, "Monthly", "diff")}
    assert pts["1m"].value == pytest.approx(0.2) and pts["1m"].unit == "pt"
    assert pts["3m"].value == pytest.approx(0.4)


def test_a_spread_crossing_zero_is_measured_in_points_not_percent():
    curve = monthly([-0.1, 0.0, 0.05, 0.1])
    [m1, m3] = change_measures(curve, "Monthly", "diff")
    assert (m1.value, m3.value) == (pytest.approx(0.05), pytest.approx(0.2))


def test_weekly_series_use_four_week_averages_and_count_the_latest_week():
    start = date(2025, 1, 4)
    weeks = [(start + timedelta(weeks=i), 200_000.0) for i in range(60)]
    weeks[-1] = (weeks[-1][0], 280_000.0)  # one bad week moves the 4-week average at once
    [m1, *_] = change_measures(weeks, "Weekly, Ending Saturday", "pct")
    assert m1.horizon == "1m"
    assert m1.value == pytest.approx(10.0)  # (3 x 200k + 280k) / 4 = 220k vs 200k


def test_quarterly_series_report_annualised_quarter_and_year():
    gdp = [
        (date(2025, 1, 1), 100.0),
        (date(2025, 4, 1), 101.0),
        (date(2025, 7, 1), 102.0),
        (date(2025, 10, 1), 103.0),
        (date(2026, 1, 1), 104.0),
    ]
    measures = {c.horizon: c for c in change_measures(gdp, "Quarterly", "pct")}
    assert measures["q/q"].unit == "% ann."
    assert measures["y/y"].value == pytest.approx(4.0)


# --- momentum in the score -------------------------------------------------------------------


def test_momentum_uses_three_month_change_in_the_right_units():
    pts = monthly([1.0, 2.0, 3.0, 5.0])
    assert momentum(pts, "Monthly", "diff") == [(date(2020, 4, 1), 4.0)]
    [(_, ann)] = momentum(monthly([100.0, 100.0, 100.0, 101.0]), "Monthly", "pct")
    assert ann == pytest.approx((1.01**4 - 1) * 100)


def test_a_turn_shows_in_momentum_before_the_level():
    # Ten years of a steady rise, then three months falling: still high, but turning down.
    values = [float(i) for i in range(120)] + [117.0, 114.0, 111.0]
    s = score_indicator(
        "X", "growth", ScoreSpec("level"), "Monthly", monthly(values, date(2016, 1, 1)), 1.0, "diff"
    )
    assert s.level_score > 1  # where it stands: still near the top of its range
    assert s.momentum_score < -1  # how it is moving: falling hard
    assert s.score == pytest.approx(0.5 * s.level_score + 0.5 * s.momentum_score)
