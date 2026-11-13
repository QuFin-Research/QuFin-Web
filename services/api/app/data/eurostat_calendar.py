"""When each Eurostat month became public, for series Eurostat serves without vintages.

Eurostat's release calendar (checked 13 Nov 2026) puts industrial production about six weeks
after the month (September data on 13 November) and the final HICP in the middle of the next
month. The API serves no release dates per period, so each is dated by a rule that errs late
(rule 9):

- industrial production (`sts_inpr_m`): the last weekday of the second month after the month;
- HICP (`prc_hicp_minr`): the last weekday of the month after.
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


def production_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 3))


def hicp_release(period: date) -> date:
    return _last_weekday_before(_first_of(period.year, period.month + 2))


RELEASES: dict[str, Callable[[date], date]] = {
    "sts_inpr_m": production_release,
    "prc_hicp_minr": hicp_release,
}


def release_of(dataset: str) -> Callable[[date], date]:
    return RELEASES[dataset]
