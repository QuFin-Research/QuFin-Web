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

- Central bank total assets (quarterly): the BIS lists a release in March, June, September and
  December, 51 to 59 days after the quarter ends (checked 17 Nov 2026 in its calendar dataflow).
  Each quarter is dated the last weekday of the second month after it ends, later than any
  listed release (the BIS also loads months between those dates; a period QuFin sees first is
  dated the day it is seen).
- Consumer prices (monthly): released 19 to 31 days after the month ends in the same calendar, so
  each month is dated the last weekday of the second month after it, which is never early.
- Total credit, debt service ratios, debt securities and global liquidity (quarterly): 156 to 171
  days after the quarter ends (global liquidity 119 to 123), so the credit rule above covers them;
  commercial property prices and international debt securities have no calendar entry that
  matches (their release months are not quarterly) and use the same, later, date.

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


def cbta_release(period: date) -> date:
    """The last weekday of the second month after the quarter that holds `period` ends."""
    quarter_end_month = (period.month + 2) // 3 * 3
    return _last_weekday_before(_first_of_month(period.year, quarter_end_month + 3))


def cpi_release(period: date) -> date:
    """The last weekday of the second month after `period` (releases come 19 to 31 days later)."""
    return _last_weekday_before(_first_of_month(period.year, period.month + 3))
