"""What admins and data scientists see: coverage, and whether the scorecard is kept current."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.data.macro_catalog import BY_ID
from app.data.scorecard_catalog import SCORED
from app.jobs import coverage_matrix
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.schemas.admin import (
    CountryGap,
    CoverageHeadline,
    CoverageSummary,
    IndicatorGap,
    JobRun,
    ScorecardStatus,
)
from app.stores.macro import MacroStore

TOP = 15  # rows in each "largest gaps" table
NO_DATA_AFTER = timedelta(days=7)  # no series loaded for this long means the backend is not running


def coverage_summary(
    session: Session, today: date, now: datetime | None = None, top: int = TOP
) -> CoverageSummary:
    cells = coverage_matrix.build(session, today)
    summary = coverage_matrix.summarize(cells)
    countries = coverage_matrix.country_gaps(cells)
    unusable = sum(v[1] for v in summary.concepts.values())
    gap = sum(v[2] for v in summary.concepts.values())
    headline = CoverageHeadline(
        countries=len(countries),
        countries_with_gaps=sum(1 for c in countries if c[4] > 0),
        applicable=summary.applicable,
        have=summary.have,
        unusable=unusable,
        gap=gap,
        coverage_pct=round(100 * summary.have / summary.applicable, 1) if summary.applicable else 0,
    )
    names = {c.concept_key: c.indicator for c in cells}
    by_indicator = [
        IndicatorGap(concept=k, indicator=names[k], have=v[0], unusable=v[1], gap=v[2])
        for k, v in sorted(summary.concepts.items(), key=lambda kv: (-kv[1][2], kv[0]))[:top]
    ]
    by_country = [
        CountryGap(iso3=c[0], country=c[1], have=c[2], unusable=c[3], gap=c[4])
        for c in sorted(countries, key=lambda c: (-c[4], c[1]))[:top]
    ]
    return CoverageSummary(
        generated_at=now or datetime.now(UTC),
        headline=headline,
        global_indicators=len(summary.concepts),
        by_indicator=by_indicator,
        by_country=by_country,
        overdue_series=sorted(c.series_id for c in cells if c.status == "OVERDUE"),
    )


def scorecard_status(
    session: Session, today: date, last_run: JobRun | None, now: datetime | None = None
) -> ScorecardStatus:
    """`updated`: every scored indicator is current. `partial`: some are overdue, so the
    scorecard still publishes but with lower confidence (the score is never filled). `stale`:
    most are overdue, or nothing has been loaded for a week."""
    now = now or datetime.now(UTC)
    store = MacroStore(session)
    releases = store.first_releases(today - LAG_WINDOW)
    stored = store.list_series()
    scored = [s for s in stored if s.meta.id in SCORED and s.meta.id in BY_ID]
    overdue, latest = [], None
    for s in scored:
        fresh = macro_status(s.meta, s.last_period, releases.get(s.meta.id, {}), today).freshness
        if not fresh.usable:
            overdue.append(s.meta.id)
        if s.last_period and (latest is None or s.last_period > latest):
            latest = s.last_period
    loaded = max((s.ingested_at for s in stored), default=None)
    usable = len(scored) - len(overdue)
    if not scored:
        state, reason = "stale", "No scored indicator is stored: load the data first."
    elif loaded is not None and now - loaded > NO_DATA_AFTER:
        state = "stale"
        reason = f"No data has been loaded for {(now - loaded).days} days."
    elif not overdue:
        state, reason = "updated", f"All {len(scored)} scored indicators are current."
    elif usable * 2 >= len(scored):
        state = "partial"
        reason = (
            f"{len(overdue)} of {len(scored)} scored indicators are overdue; they are left out "
            "and the scorecard's confidence is lower."
        )
    else:
        state = "stale"
        reason = f"{len(overdue)} of {len(scored)} scored indicators are overdue."
    if last_run is not None and last_run.status in ("failed", "interrupted"):
        reason += f" The last refresh {last_run.status}."
    return ScorecardStatus(
        state=state,  # type: ignore[arg-type]
        reason=reason,
        latest_period=latest,
        scored_series=len(scored),
        usable_series=usable,
        overdue_series=sorted(overdue),
        data_loaded_at=loaded,
    )
