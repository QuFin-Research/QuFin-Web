"""When national-portal values became public, for series served without vintages.

Neither the Banco Central do Brasil SGS nor the SingStat Table Builder gives a release date per
value, so each period is dated by a rule that errs late (rule 9). Read from the usual pattern of
the suppliers' release calendars (not each year's; unverified):

- Brazil, unemployment (PNAD Continua moving quarter) and goods trade balance: published in the
  month after; dated the last weekday of that month;
- Singapore, quarterly unemployment: the advance Labour Force Survey comes out at the end of the
  month after the quarter; dated the last weekday of that month.
"""

from datetime import date, timedelta


def _last_weekday_before(first_of_next_month: date) -> date:
    day = first_of_next_month - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day


def _first_of(year: int, month: int) -> date:
    year += (month - 1) // 12
    return date(year, (month - 1) % 12 + 1, 1)


def brazil_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 2))


def singapore_quarterly_release(period: date) -> date:
    """A quarter starting on 1 July is dated 31 October (the last weekday before 1 November)."""
    return _last_weekday_before(_first_of(period.year, period.month + 4))
