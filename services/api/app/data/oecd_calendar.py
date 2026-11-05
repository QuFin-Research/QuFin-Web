"""When each OECD composite leading indicator and confidence reading became public.

The OECD publishes them monthly, around mid-month, through its API and press release; some
countries' inputs arrive a month later than others (on 6 Nov 2026 the latest month was
September for most series, August for the US and Turkish leading indicators). The API serves
no release dates, so every month is dated the 15th of the second month after it (next
weekday): late for most series, never early for the slower ones (rule 9).
"""

from datetime import date, timedelta


def oecd_release(period: date) -> date:
    months = period.month + 1  # zero-based month index two months on
    day = date(period.year + months // 12, months % 12 + 1, 15)
    while day.weekday() > 4:
        day += timedelta(days=1)
    return day
