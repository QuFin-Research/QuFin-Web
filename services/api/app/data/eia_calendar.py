"""When each week of the EIA Weekly Petroleum Status Report became public.

The report covers the week ending Friday and is normally released the following Wednesday at
10:30 ET; when a federal holiday falls on the Monday to Wednesday of the release week, the release
moves back a day. The EIA API serves today's values only, with no release history, so historical
release dates are derived from this rule (rule 9 in services/api/CLAUDE.md): it errs late, never
early. Holiday dates come from the same federal calendar the CFTC dates use.
"""

from datetime import date, timedelta

from app.data.cot_calendar import federal_holidays


def wpsr_release_date(week_ending: date) -> date:
    """The day the week ending `week_ending` (a Friday) was published."""
    friday = week_ending + timedelta(days=(4 - week_ending.weekday()) % 7)
    monday = friday + timedelta(days=3)
    release = friday + timedelta(days=5)  # Wednesday
    if any(monday + timedelta(days=d) in federal_holidays(monday.year) for d in range(3)):
        release += timedelta(days=1)
    while release.weekday() > 4 or release in federal_holidays(release.year):
        release += timedelta(days=1)
    return release
