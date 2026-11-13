"""When each World Bank annual value became public.

World Development Indicators are updated through the year as national offices report, and the API
serves no release date per value. On 13 Nov 2026 it already held 2025 for most economies, so the
first estimate of a year can be public within the year itself; the rule dates every year at the
end of the following year, which is never early (rule 9) and is what the release check measures
the next year's due date from.
"""

from datetime import date


def annual_release(period: date) -> date:
    """31 December of the year after the one the value describes."""
    return date(period.year + 1, 12, 31)
