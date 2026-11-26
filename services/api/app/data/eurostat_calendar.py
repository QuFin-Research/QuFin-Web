"""When each Eurostat month became public, for series Eurostat serves without vintages.

Eurostat's release calendar (checked 13 Nov 2026) puts industrial production about six weeks
after the month (September data on 13 November) and the final HICP in the middle of the next
month. The API serves no release dates per period, so each is dated by a rule that errs late
(rule 9):

- industrial production (`sts_inpr_m`): the last weekday of the second month after the month;
- HICP (`prc_hicp_minr`): the last weekday of the month after. Eurostat publishes the final HICP
  15 to 18 days after the month and early figures (flag `e`) before that; a period first read
  earlier than this date is dated by that first read (`record_latest`, rule 9), and the final
  figure arrives as a revision, so the flash and the final are kept as separate vintages.
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


def quarterly_release(period: date) -> date:
    """A quarter (dated at its first month): the last weekday of the third month after it.
    GDP is out about 65 days after the quarter and the balance of payments about 85."""
    return _last_weekday_before(_first_of(period.year, period.month + 6))


def hpi_release(period: date) -> date:
    """Date HPI conservatively on the 15th of the fourth month after the quarter."""
    return _first_of(period.year, period.month + 6) + timedelta(days=14)


RELEASES: dict[str, Callable[[date], date]] = {
    "namq_10_gdp": quarterly_release,
    "ei_bpm6ca_q": quarterly_release,
    "prc_hpi_q": hpi_release,
    "ei_eteu27_2020_m": production_release,  # trade is out about six weeks after the month
    "sts_inpr_m": production_release,
    "prc_hicp_minr": hicp_release,
    "une_rt_m": hicp_release,  # unemployment follows the month by about four weeks
}


def release_of(dataset: str) -> Callable[[date], date]:
    return RELEASES[dataset]
