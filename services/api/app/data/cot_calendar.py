"""When each CFTC Commitments of Traders report actually became public.

A report holds positions as of a Tuesday (or the Monday, when Tuesday is a holiday) and is
normally released that Friday at 3:30 pm ET. Using a report before it was public is look-ahead,
so the release date must be right, including the weeks it was late:

- Federal holidays: "Federal holidays may delay release by one or two days" (CFTC release
  schedule). Rule: a federal holiday after the as-of date and up to that Friday moves the
  release to the next business day. It reproduces every delayed week in the CFTC's 2026
  schedule and its 2015, 2021 and 2025 holiday notices; where it may be a day late (a Tuesday
  holiday absorbed by a Monday as-of date) it errs late, which never leaks data.
- Documented exceptions (KNOWN_RELEASES), from the CFTC's Historical Special Announcements:
  https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm
- The 2018-19 shutdown: the CFTC published no per-week dates, only the rule "one report on
  Tuesday and another on Friday of each week until the reports are current", starting Friday
  1 February 2019 (press release 7864-19). Those dates are derived from that rule
  (DERIVED_RELEASES) and are not confirmed one by one.

Times of day are not stated for late releases, so a report counts as public only from its
release date's close; point-in-time reads compare dates, never earlier.
"""

from datetime import date, timedelta
from functools import cache


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


@cache
def federal_holidays(year: int) -> frozenset[date]:
    """US federal holidays as observed (5 U.S.C. 6103)."""
    mon, thu = 0, 3
    days = {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, mon, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, mon, 3),  # Washington's Birthday
        _last_weekday(year, 5, mon),  # Memorial Day
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, mon, 1),  # Labor Day
        _nth_weekday(year, 10, mon, 2),  # Columbus Day
        _observed(date(year, 11, 11)),  # Veterans Day
        _nth_weekday(year, 11, thu, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),
    }
    if year >= 2021:
        days.add(_observed(date(year, 6, 19)))  # Juneteenth
    # New Year's Day falling on a Saturday is observed on the previous year's 31 December.
    if date(year + 1, 1, 1).weekday() == 5:
        days.add(date(year, 12, 31))
    return frozenset(days)


def _is_business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in federal_holidays(day.year)


# As-of date -> actual (or CFTC-announced) release date.
KNOWN_RELEASES: dict[date, date] = {
    date(2015, 6, 30): date(2015, 7, 6),  # July 3 holiday; a premature July 3 file was withdrawn
    date(2020, 12, 21): date(2020, 12, 28),  # extra federal holiday on 24 December
    date(2021, 6, 15): date(2021, 6, 21),  # Juneteenth, first observed 18 June 2021
    date(2025, 1, 7): date(2025, 1, 13),  # national day of mourning, 9 January
    # 2023 ION cyber incident: delayed reports, released on the announcement dates.
    date(2023, 1, 31): date(2023, 2, 24),
    date(2023, 2, 7): date(2023, 3, 3),
    date(2023, 2, 14): date(2023, 3, 8),
    date(2023, 2, 21): date(2023, 3, 10),
    date(2023, 2, 28): date(2023, 3, 14),
    date(2023, 3, 7): date(2023, 3, 16),
    date(2023, 3, 14): date(2023, 3, 21),
    # 2025 shutdown: CFTC catch-up schedule of 9 December 2025 ("new publish date").
    date(2025, 9, 30): date(2025, 11, 19),
    date(2025, 10, 7): date(2025, 11, 21),
    date(2025, 10, 14): date(2025, 11, 25),
    date(2025, 10, 21): date(2025, 12, 2),
    date(2025, 10, 28): date(2025, 12, 5),
    date(2025, 11, 4): date(2025, 12, 9),
    date(2025, 11, 10): date(2025, 12, 10),
    date(2025, 11, 18): date(2025, 12, 12),
    date(2025, 11, 25): date(2025, 12, 15),
    date(2025, 12, 2): date(2025, 12, 17),
    date(2025, 12, 9): date(2025, 12, 19),
    date(2025, 12, 16): date(2025, 12, 23),
    date(2025, 12, 23): date(2025, 12, 29),
}

# 2018-19 shutdown, derived from the CFTC's catch-up rule (see the module docstring).
_SHUTDOWN_2019_AS_OF = (
    date(2018, 12, 24),
    date(2018, 12, 31),
    date(2019, 1, 8),
    date(2019, 1, 15),
    date(2019, 1, 22),
    date(2019, 1, 29),
    date(2019, 2, 5),
    date(2019, 2, 12),
    date(2019, 2, 19),
    date(2019, 2, 26),
)
_SHUTDOWN_2019_RELEASES = (
    date(2019, 2, 1),
    date(2019, 2, 5),
    date(2019, 2, 8),
    date(2019, 2, 12),
    date(2019, 2, 15),
    date(2019, 2, 19),
    date(2019, 2, 22),
    date(2019, 2, 26),
    date(2019, 3, 1),
    date(2019, 3, 5),
)
DERIVED_RELEASES: dict[date, date] = dict(
    zip(_SHUTDOWN_2019_AS_OF, _SHUTDOWN_2019_RELEASES, strict=True)
)


def release_date(as_of: date) -> date:
    """The day a report with positions as of `as_of` became public."""
    if as_of in KNOWN_RELEASES:
        return KNOWN_RELEASES[as_of]
    if as_of in DERIVED_RELEASES:
        return DERIVED_RELEASES[as_of]
    friday = as_of + timedelta(days=(4 - as_of.weekday()) % 7)
    delayed = any(
        not _is_business_day(as_of + timedelta(days=d))
        and (as_of + timedelta(days=d)).weekday() < 5
        for d in range(1, (friday - as_of).days + 1)
    )
    release = friday
    if delayed:
        release = friday + timedelta(days=1)
        while not _is_business_day(release):
            release += timedelta(days=1)
    return release
