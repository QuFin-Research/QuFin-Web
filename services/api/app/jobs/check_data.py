"""Check every stored data source against its release schedule (see app.domain.freshness)."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data.macro_catalog import BY_ID, CATALOG, CatalogSeries
from app.data.positioning_catalog import COT_CONTRACTS
from app.data.scorecard_catalog import SCORED
from app.domain.freshness import Freshness, Timeliness, assess, timeliness
from app.stores.macro import MacroStore, SeriesMeta
from app.stores.positioning import CotReport, PositioningStore

# Release lags are measured over recent periods, so a changed release calendar shows up.
LAG_WINDOW = timedelta(days=3 * 365)
COT_FREQUENCY = "Weekly"


@dataclass(frozen=True)
class SeriesStatus:
    freshness: Freshness
    timeliness: Timeliness
    # When the source (e.g. the University of Michigan) first published the latest period,
    # and when FRED shows it: later by the catalog's declared delay, else the same day.
    latest_source_release: date | None
    latest_fred_release: date | None


@dataclass(frozen=True)
class DataCheck:
    source: str
    id: str
    frequency: str
    last_period: date | None
    status: SeriesStatus


# Units that say the source already publishes a change ("Percent Change from Year Ago", ...).
_CHANGE_UNITS = re.compile(r"\bchange\b|\bgrowth\b", re.IGNORECASE)


def double_change_reason(meta: SeriesMeta, entry: CatalogSeries | None) -> str | None:
    """A series published as a change must not be changed again (percent change or y/y)."""
    if entry is None:
        return None
    already = entry.published_as_change or bool(_CHANGE_UNITS.search(meta.units))
    if not already:
        return None
    spec = SCORED.get(entry.id)
    if entry.change == "pct" or (spec is not None and spec.transform == "yoy"):
        return (
            f"The source already publishes {entry.id} as a change ({meta.units}); a percent "
            "change or year-on-year transform would be a change of a change"
        )
    return None


def _review_reason(meta: SeriesMeta, declared_delay: int) -> str | None:
    if reason := double_change_reason(meta, BY_ID.get(meta.id)):
        return reason
    if meta.delay_notice and declared_delay == 0:
        return (
            "FRED reports a publication delay the catalog does not account for: "
            f"{meta.delay_notice}"
        )
    if declared_delay and not meta.delay_notice:
        return "The catalog declares a FRED delay that FRED no longer reports; review it"
    return None


def macro_status(
    meta: SeriesMeta, last_period: date | None, first_releases: Mapping[date, date], today: date
) -> SeriesStatus:
    entry = BY_ID.get(meta.id)
    delay = entry.fred_delay_days if entry else 0
    lags = [(released - period).days for period, released in first_releases.items()]
    fresh = assess(
        title=meta.title,
        frequency=meta.frequency,
        last_period=last_period,
        release_lags=lags,
        today=today,
        fred_delay_days=delay,
        review_reason=_review_reason(meta, delay),
    )
    released = first_releases.get(last_period) if last_period else None
    return SeriesStatus(
        fresh,
        timeliness(meta.frequency, lags, delay, fresh.usable),
        released,
        released + timedelta(days=delay) if released else None,
    )


def cot_status(reports: Sequence[CotReport], today: date) -> SeriesStatus:
    recent = reports[-52:]
    lags = [(r.release_date - r.report_date).days for r in recent]
    fresh = assess(
        title="",
        frequency=COT_FREQUENCY,
        last_period=reports[-1].report_date if reports else None,
        release_lags=lags,
        today=today,
    )
    released = reports[-1].release_date if reports else None
    return SeriesStatus(fresh, timeliness(COT_FREQUENCY, lags, 0, fresh.usable), released, released)


def check_macro(session: Session, today: date) -> list[DataCheck]:
    """Every catalog series; one that was never ingested counts as overdue."""
    store = MacroStore(session)
    summaries = {s.meta.id: s for s in store.list_series()}
    releases = store.first_releases(today - LAG_WINDOW)
    checks = []
    for entry in CATALOG:
        summary = summaries.get(entry.id)
        if summary is None:
            missing = SeriesStatus(
                Freshness("overdue", None, 0, 0, "Not ingested"),
                Timeliness(0, 0, 0, 0.0),
                None,
                None,
            )
            checks.append(DataCheck("fred", entry.id, "", None, missing))
            continue
        status = macro_status(summary.meta, summary.last_period, releases.get(entry.id, {}), today)
        checks.append(
            DataCheck("fred", entry.id, summary.meta.frequency, summary.last_period, status)
        )
    return checks


def check_positioning(session: Session, today: date) -> list[DataCheck]:
    store = PositioningStore(session)
    checks = []
    for contract in COT_CONTRACTS:
        reports = store.history(contract.code)
        last = reports[-1].report_date if reports else None
        checks.append(
            DataCheck("cftc", contract.symbol, COT_FREQUENCY, last, cot_status(reports, today))
        )
    return checks


def check_all(session: Session, today: date) -> list[DataCheck]:
    return check_macro(session, today) + check_positioning(session, today)


def format_report(checks: Sequence[DataCheck]) -> str:
    lines = [
        f"{'source':<6} {'series':<20} {'frequency':<12} {'last period':<12} {'weight':>6}  status"
    ]
    for c in checks:
        f = c.status.freshness
        flag = "OK" if f.usable else f.status.upper()
        lines.append(
            f"{c.source:<6} {c.id:<20} {c.frequency[:12]:<12} {c.last_period or '-'!s:<12} "
            f"{c.status.timeliness.weight:>6.2f}  {flag:<12} {f.reason}"
        )
    failed = [c for c in checks if not c.status.freshness.usable]
    lines.append(
        f"{len(checks) - len(failed)} of {len(checks)} on schedule"
        + (f"; NOT USABLE: {', '.join(c.id for c in failed)}" if failed else "")
    )
    return "\n".join(lines)
