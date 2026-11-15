"""When each BIS series month or quarter became public.

The BIS publishes a release calendar (bis.org/statistics/relcal.htm, checked 12 Nov 2026) but
its API serves no release dates, and the calendar covers only 2023 onwards, so earlier periods
are dated by a rule that errs late (rule 9). The rule was tested against every date in that
calendar:

- Policy rates and effective exchange rates (monthly): the BIS releases a month during the
  following month, on Thursdays (policy rates are refreshed weekly as banks report; effective
  exchange rates once, between the 15th and the 28th). Each month is dated the last weekday of
  the following month, which is never before any listed release.
- Credit and credit-to-GDP gaps (quarterly): released in March, June, September and December,
  156 to 171 days after the quarter ends (2023 Q1 to 2026 Q1). Each quarter is dated the last
  weekday of the sixth month after it ends (a quarter ending 31 March, September 30), 183 days.

A period QuFin first sees before its derived date is dated the day it is seen (record_latest).
"""

from datetime import date, timedelta


def _last_weekday_before(first_of_next_month: date) -> date:
    day = first_of_next_month - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day


def _first_of_month(year: int, month: int) -> date:
    """The first day of a month, however far `month` runs past 12."""
    year += (month - 1) // 12
    return date(year, (month - 1) % 12 + 1, 1)


def monthly_release(period: date) -> date:
    """The last weekday of the month after `period` (any day of the reported month)."""
    return _last_weekday_before(_first_of_month(period.year, period.month + 2))


def quarterly_release(period: date) -> date:
    """The last weekday of the sixth month after the quarter that starts on `period`."""
    # The quarter ends in month+2; six months later is month+8.
    return _last_weekday_before(_first_of_month(period.year, period.month + 9))
