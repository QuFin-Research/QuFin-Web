"""When each Treasury Fiscal Data record became public (Bureau of the Fiscal Service).

Fiscal Data's release calendar (api.fiscaldata.treasury.gov/services/calendar/release) lists
only upcoming and latest releases, so past dates are derived from its pattern, checked on
5 Nov 2026 (rule 9, erring late):
- Debt to the Penny: each business day at 4:15 pm ET, for the previous business day.
- Average Interest Rates and Interest Expense on the Public Debt: 3 pm ET on the fourth
  business day of the following month (October 2026 on 5 November, November on 4 December).
Holiday dates come from the same federal calendar the CFTC dates use.
"""

from datetime import date, timedelta

from app.data.cot_calendar import federal_holidays


def _business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in federal_holidays(day.year)


def next_business_day(day: date) -> date:
    day += timedelta(days=1)
    while not _business_day(day):
        day += timedelta(days=1)
    return day


def debt_to_penny_release(record_date: date) -> date:
    """Published the business day after the day it reports."""
    return next_business_day(record_date)


def monthly_release(period: date) -> date:
    """The fourth business day of the month after `period` (any day of the reported month)."""
    first = date(period.year + period.month // 12, period.month % 12 + 1, 1)
    day = first if _business_day(first) else next_business_day(first)
    for _ in range(3):
        day = next_business_day(day)
    return day
