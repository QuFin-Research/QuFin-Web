"""CFTC release dates must match what the CFTC published, so backtests never see a report early."""

from datetime import date

import pytest

from app.data.cot_calendar import federal_holidays, release_date

# CFTC 2026 release schedule (cftc.gov, Commitments of Traders release schedule): the weeks
# marked "Delayed release date due to a federal holiday".
DELAYED_2026 = {
    date(2025, 12, 30): date(2026, 1, 5),
    date(2026, 6, 16): date(2026, 6, 22),
    date(2026, 6, 30): date(2026, 7, 6),
    date(2026, 11, 10): date(2026, 11, 16),
    date(2026, 11, 24): date(2026, 11, 30),
    date(2026, 12, 22): date(2026, 12, 28),
}


@pytest.mark.parametrize(("as_of", "released"), DELAYED_2026.items())
def test_holiday_weeks_match_the_cftc_2026_schedule(as_of, released):
    assert release_date(as_of) == released


def test_every_other_2026_week_is_released_on_friday():
    as_of = date(2026, 1, 6)
    while as_of < date(2026, 12, 29):  # the next week releases in 2027
        if as_of not in DELAYED_2026:
            released = release_date(as_of)
            assert released.weekday() == 4 and (released - as_of).days == 3, as_of
        as_of = date.fromordinal(as_of.toordinal() + 7)


@pytest.mark.parametrize(
    ("as_of", "released"),
    [
        (date(2015, 6, 30), date(2015, 7, 6)),  # July 3 notice
        (date(2021, 6, 15), date(2021, 6, 21)),  # first Juneteenth
        (date(2020, 12, 21), date(2020, 12, 28)),  # extra Christmas Eve holiday
        (date(2025, 1, 7), date(2025, 1, 13)),  # national day of mourning
        (date(2023, 2, 7), date(2023, 3, 3)),  # ION cyber incident
        (date(2025, 9, 30), date(2025, 11, 19)),  # 2025 shutdown catch-up
        (date(2025, 12, 23), date(2025, 12, 29)),  # back on schedule
        (date(2018, 12, 24), date(2019, 2, 1)),  # 2018-19 shutdown, first catch-up release
        (date(2019, 2, 26), date(2019, 3, 5)),  # last catch-up release
        (date(2019, 3, 5), date(2019, 3, 8)),  # current again
    ],
)
def test_documented_late_releases(as_of, released):
    assert release_date(as_of) == released


def test_federal_holidays_include_observed_days():
    h2026 = federal_holidays(2026)
    assert date(2026, 7, 3) in h2026  # July 4 is a Saturday
    assert date(2026, 11, 26) in h2026  # Thanksgiving
    assert date(2020, 6, 19) not in federal_holidays(2020)  # Juneteenth from 2021
    assert date(2021, 12, 31) in federal_holidays(2021)  # New Year 2022 is a Saturday


def test_a_report_is_never_public_before_friday():
    as_of = date(2015, 1, 6)
    while as_of < date(2026, 11, 1):
        assert (release_date(as_of) - as_of).days >= 3
        as_of = date.fromordinal(as_of.toordinal() + 7)
