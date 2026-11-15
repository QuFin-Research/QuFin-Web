"""Frequency harmonisation and PoC (Rules D, E, G): down-sampling, completeness, change units."""

from datetime import date, timedelta

import pytest

from app.domain.harmonize import (
    Obs,
    adjustment_tag,
    aggregate,
    aggregation_for,
    allowed_frequencies,
    native_frequency,
    poc,
)


def monthly(first: date, values: list[float]) -> list[Obs]:
    return [
        Obs(date(first.year + (first.month - 1 + i) // 12, (first.month - 1 + i) % 12 + 1, 1), v)
        for i, v in enumerate(values)
    ]


def test_native_frequency_reads_the_sources_wording():
    assert native_frequency("Weekly, Ending Friday") == "weekly"
    assert native_frequency("Monthly, End of Period") == "monthly"
    assert native_frequency("Quarterly") == "quarterly"
    with pytest.raises(ValueError):
        native_frequency("Fortnightly")


def test_adjustment_is_sa_nsa_or_other_never_guessed():
    assert adjustment_tag("Seasonally Adjusted") == "SA"
    assert adjustment_tag("Seasonally Adjusted Annual Rate") == "SA"
    assert adjustment_tag("Not Seasonally Adjusted") == "NSA"
    assert adjustment_tag("Amplitude Adjusted (OECD)") == "OTHER"


def test_the_aggregation_follows_what_the_series_is():
    assert aggregation_for("rate_percent", "unemployment_rate") == "mean"
    assert aggregation_for("count", "initial_jobless_claims") == "sum"
    assert aggregation_for("amount_currency", "government_debt_outstanding") == "end"


def test_allowed_frequencies_stop_at_the_slowest_series_and_say_why():
    allowed = allowed_frequencies([("US CPI", "monthly"), ("UK claims", "weekly")])
    assert allowed.frequencies == ["monthly", "quarterly", "semi_annual", "annual"]
    assert allowed.common == "monthly"
    assert allowed.limiting == "US CPI"
    assert "Monthly, Quarterly, Semi-Annual and Annual" in (allowed.notice or "")
    assert "US CPI" in (allowed.notice or "")
    assert allowed_frequencies([("x", "daily")]).notice is None


def test_monthly_becomes_quarterly_by_end_mean_or_sum_and_drops_a_part_quarter():
    series = monthly(date(2026, 1, 1), [1, 2, 3, 4, 5, 6, 7])  # July has no quarter-mates
    assert [p.value for p in aggregate(series, "monthly", "quarterly", "end")] == [3, 6]
    assert [p.value for p in aggregate(series, "monthly", "quarterly", "mean")] == [2, 5]
    assert [p.value for p in aggregate(series, "monthly", "quarterly", "sum")] == [6, 15]
    assert aggregate(series, "monthly", "quarterly", "end")[0].period == date(2026, 1, 1)


def test_weekly_becomes_monthly_and_the_unfinished_month_is_left_out():
    weeks = [
        Obs(date(2026, 9, 5) + timedelta(days=7 * i), 10.0 + i) for i in range(9)
    ]  # Sat 5 Sep .. Sat 31 Oct
    months = aggregate(weeks, "weekly", "monthly", "mean")
    assert [m.period for m in months] == [date(2026, 9, 1), date(2026, 10, 1)]
    # A week short of the month's end, October is not a month yet and is dropped.
    assert [m.period for m in aggregate(weeks[:-1], "weekly", "monthly", "mean")] == [
        date(2026, 9, 1)
    ]


def test_same_frequency_passes_through_and_up_sampling_is_refused():
    series = monthly(date(2026, 1, 1), [1, 2, 3])
    assert aggregate(series, "monthly", "monthly", "end") == series
    with pytest.raises(ValueError):
        aggregate(series, "monthly", "weekly", "end")


def test_poc_is_percent_for_levels_and_points_for_rates():
    levels = monthly(date(2026, 1, 1), [100, 110, 99])
    changes, unit = poc(levels, "monthly", in_points=False)
    assert unit == "%" and [round(p.value, 6) for p in changes] == [10.0, -10.0]
    rates = monthly(date(2026, 1, 1), [4.0, 4.3, 4.1])
    diffs, unit = poc(rates, "monthly", in_points=True)
    assert unit == "pp" and [round(p.value, 6) for p in diffs] == [0.3, -0.2]


def test_poc_skips_a_zero_or_negative_base_and_never_bridges_a_gap():
    series = [
        Obs(date(2026, 1, 1), 0.0),
        Obs(date(2026, 2, 1), 5.0),
        Obs(date(2026, 3, 1), -1.0),
        Obs(date(2026, 4, 1), 2.0),
        Obs(date(2026, 6, 1), 3.0),  # May is missing
    ]
    changes, _ = poc(series, "monthly", in_points=False)
    assert [p.period for p in changes] == [date(2026, 3, 1)]  # 5 -> -1 only; no zero/negative base


def test_a_series_already_published_as_a_change_is_not_changed_again():
    series = monthly(date(2026, 1, 1), [3.1, 3.0])
    values, unit = poc(series, "monthly", in_points=True, published_as_change=True)
    assert unit == "as published" and values == series
