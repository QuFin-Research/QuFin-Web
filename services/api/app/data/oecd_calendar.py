"""When each OECD composite leading indicator and confidence reading became public.

The OECD publishes them monthly, around mid-month, through its API and press release; some
countries' inputs arrive a month later than others (on 6 Nov 2026 the latest month was
September for most series, August for the US and Turkish leading indicators). The API serves
no release dates, so every month is dated the 15th of the second month after it (next
weekday): late for most series, never early for the slower ones (rule 9).
"""

from datetime import date, timedelta


def oecd_quarterly_release(period: date) -> date:
    """A quarter (dated at its first month): the 15th of the fourth month after its end, next
    weekday. Quarterly accounts and the balance of payments reach the OECD about three months
    after the quarter; the API serves no release dates, so this errs late (rule 9)."""
    months = period.month + 6
    day = date(period.year + (months - 1) // 12, (months - 1) % 12 + 1, 15)
    while day.weekday() > 4:
        day += timedelta(days=1)
    return day


def oecd_release(period: date) -> date:
    months = period.month + 1  # zero-based month index two months on
    day = date(period.year + months // 12, months % 12 + 1, 15)
    while day.weekday() > 4:
        day += timedelta(days=1)
    return day
