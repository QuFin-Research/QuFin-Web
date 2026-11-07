"""When each IMF International Liquidity month became public.

The IMF API serves no release dates and the IMF publishes no release calendar for these tables;
on 7 Nov 2026 the latest month was September for most economies and August for the rest. Each
month is dated the last weekday of the second month after it (September 2026 on 30 November):
late for most economies and never early for the slower ones (rule 9).
"""

from datetime import date, timedelta


def imf_release(period: date) -> date:
    months = period.month + 2  # the month after the second month on, zero-based
    day = date(period.year + months // 12, months % 12 + 1, 1) - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day
