"""When each ONS period became public, for series the ONS publishes without vintages.

The ONS time series carry no release dates per period, so each is dated by a rule that errs late
(rule 9), read from the usual pattern of the ONS release calendar (checked 13 Nov 2026):

- labour market (unemployment rate, a rolling three-month window dated by its last month):
  published in the middle of the second month after (July in mid-September); dated the last
  weekday of that month;
- consumer price inflation (monthly): published in the third week of the next month; dated the
  last weekday of the next month;
- quarterly national accounts (GDP): the first estimate follows within about six weeks and the
  full quarterly accounts about three months after the quarter ends; a quarter starting on
  1 April is dated 30 September (the last weekday of the sixth month from its start).
"""

from collections.abc import Callable
from datetime import date, timedelta


def _last_weekday_before(first_of_next_month: date) -> date:
    day = first_of_next_month - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day


def _first_of(year: int, month: int) -> date:
    year += (month - 1) // 12
    return date(year, (month - 1) % 12 + 1, 1)


def labour_market_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 3))


def inflation_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 2))


def national_accounts_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 6))


RELEASES: dict[str, dict[str, Callable[[date], date]]] = {
    "Monthly": {"MGSX": labour_market_release, "DKO8": inflation_release},
    "Quarterly": {"ABMI": national_accounts_release},
}


def release_for(frequency: str, cdid: str) -> Callable[[date], date]:
    return RELEASES[frequency][cdid]
