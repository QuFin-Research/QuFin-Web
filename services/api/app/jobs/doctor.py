"""QuFin Doctor: fast, deterministic health checks of the macro database, with safe repairs (N).

`uv run python -m app.cli doctor` reports; `--fix` repairs what can be repaired without guessing:

- rows that belong to no series (orphaned vintages) and values that are not finite are deleted;
- series the catalog no longer lists are removed (the same prune the FRED job runs);
- canonical codes that no longer match a series' frequency or adjustment are re-derived.

A destructive repair first copies the database to `<name>.doctor-<timestamp>.db` and the report
says what was done. Everything else is only flagged, because choosing the right series, the right
source or the right date is a decision for a person: duplicate country-indicator pairs (Rule M),
overlapping or reversed vintage dates, series missing or frozen upstream (quarantine means taking
it out of the catalog, with the reason recorded), and countries that have no data yet.
"""

import shutil
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID
from app.data.taxonomy import COUNTRIES, COUNTRY_BY_ISO2, TaxonomyError, canonical_code
from app.domain.harmonize import adjustment_tag
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.jobs.ingest_fred import prune
from app.stores.macro import MacroStore

EXPECTED_COUNTRIES = 85  # the QuFin Country List (Rule J)
Level = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    check: str
    level: Level
    subject: str
    detail: str
    fixed: bool = False


@dataclass(frozen=True)
class DoctorReport:
    findings: list[Finding]
    backup: Path | None

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error" and not f.fixed]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning" and not f.fixed]


def backup_database(session: Session, now: datetime | None = None) -> Path | None:
    """Copy a file-based SQLite database next to itself; None for any other database."""
    url = make_url(str(session.get_bind().engine.url))
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    source = Path(url.database)
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    target = source.with_name(f"{source.stem}.doctor-{stamp}.db")
    session.commit()  # release locks so the copy is whole
    shutil.copyfile(source, target)
    return target


def _scalar(session: Session, sql: str) -> int:
    return int(session.execute(text(sql)).scalar() or 0)


class _Run:
    def __init__(self, session: Session, today: date, fix: bool, quick: bool) -> None:
        self.session, self.today, self.fix, self.quick = session, today, fix, quick
        self.findings: list[Finding] = []
        self.backup: Path | None = None

    def add(self, check: str, level: Level, subject: str, detail: str, fixed: bool = False) -> None:
        self.findings.append(Finding(check, level, subject, detail, fixed))

    def _backup_once(self) -> None:
        if self.backup is None:
            self.backup = backup_database(self.session)

    # --- checks ------------------------------------------------------------------------------

    def orphans(self) -> None:
        n = _scalar(
            self.session,
            "SELECT COUNT(*) FROM macro_observations o "
            "WHERE NOT EXISTS (SELECT 1 FROM macro_series s WHERE s.id = o.series_id)",
        )
        if not n:
            return
        if self.fix:
            self._backup_once()
            self.session.execute(
                text(
                    "DELETE FROM macro_observations WHERE NOT EXISTS "
                    "(SELECT 1 FROM macro_series s WHERE s.id = macro_observations.series_id)"
                )
            )
            self.session.commit()
        self.add("orphaned vintages", "error", "macro_observations", f"{n} rows", self.fix)

    def corrupt_values(self) -> None:
        n = _scalar(
            self.session,
            "SELECT COUNT(*) FROM macro_observations WHERE value > 1e300 OR value < -1e300",
        )
        if not n:
            return
        if self.fix:
            self._backup_once()
            self.session.execute(
                text("DELETE FROM macro_observations WHERE value > 1e300 OR value < -1e300")
            )
            self.session.commit()
        self.add("non-finite values", "error", "macro_observations", f"{n} rows", self.fix)

    def date_order(self) -> None:
        reversed_ = _scalar(
            self.session,
            "SELECT COUNT(*) FROM macro_observations WHERE realtime_start > realtime_end",
        )
        if reversed_:
            self.add(
                "vintage dates",
                "error",
                "macro_observations",
                f"{reversed_} rows start after they end",
            )
        if self.quick:
            return
        overlap = _scalar(
            self.session,
            "SELECT COUNT(*) FROM (SELECT realtime_start AS s, "
            "LAG(realtime_end) OVER (PARTITION BY series_id, period ORDER BY realtime_start) AS e "
            "FROM macro_observations) WHERE e IS NOT NULL AND s <= e",
        )
        if overlap:
            self.add(
                "vintage dates",
                "error",
                "macro_observations",
                f"{overlap} vintages overlap the one before them (one period, two values at once)",
            )

    def adjustment_tags(self) -> None:
        store = MacroStore(self.session)
        stale = []
        for s in store.list_series():
            meta = s.meta
            if not meta.seasonal_adjustment.strip():
                self.add("SA/NSA tag", "error", meta.id, "no seasonal adjustment stated")
                continue
            try:
                expected = canonical_code(
                    meta.id, meta.country, meta.frequency, meta.seasonal_adjustment
                )
            except TaxonomyError as exc:
                self.add("canonical code", "error", meta.id, str(exc))
                continue
            if expected is not None and expected != meta.canonical_code:
                stale.append(meta.id)
            if (
                adjustment_tag(meta.seasonal_adjustment) == "OTHER"
                and meta.canonical_code
                and meta.canonical_code.endswith((".SA", ".NSA"))
            ):
                self.add(
                    "SA/NSA tag",
                    "error",
                    meta.id,
                    f"{meta.seasonal_adjustment!r} is neither SA nor NSA but the code says so",
                )
        if stale:
            if self.fix:
                from app.jobs.sync_taxonomy import sync

                sync(self.session)
                self.session.commit()
            self.add(
                "canonical code",
                "error",
                ", ".join(stale[:5]) + (" ..." if len(stale) > 5 else ""),
                f"{len(stale)} codes differ from the series' frequency or adjustment",
                self.fix,
            )

    def duplicates(self) -> None:
        stored = {s.meta.id: s.meta for s in MacroStore(self.session).list_series()}
        seen: dict[tuple[str, str], list[str]] = defaultdict(list)
        for series_id, meta in stored.items():
            concept = SERIES_CONCEPTS.get((meta.country, series_id))
            if concept:
                seen[(meta.country, concept)].append(series_id)
        for (country, concept), ids in sorted(seen.items()):
            if len(ids) > 1:
                sources = ", ".join(f"{i} ({stored[i].source})" for i in ids)
                self.add("duplicate indicator", "error", f"{country} {concept}", sources)

    def catalog(self) -> None:
        stored = {s.meta.id for s in MacroStore(self.session).list_series()}
        extra = sorted(stored - set(BY_ID))
        if extra:
            if self.fix:
                self._backup_once()
                prune(self.session)
                self.session.commit()
            self.add(
                "stale series",
                "warning",
                ", ".join(extra),
                "stored but not in the catalog",
                self.fix,
            )
        missing = sorted(set(BY_ID) - stored)
        if missing:
            self.add(
                "missing series",
                "error",
                ", ".join(missing[:6]) + (" ..." if len(missing) > 6 else ""),
                f"{len(missing)} catalog series have never been ingested",
            )

    def frozen(self) -> None:
        store = MacroStore(self.session)
        releases = store.first_releases(self.today - LAG_WINDOW)
        for s in store.list_series():
            if s.meta.id not in BY_ID:
                continue
            status = macro_status(s.meta, s.last_period, releases.get(s.meta.id, {}), self.today)
            if not status.freshness.usable:
                self.add(
                    "frozen or overdue",
                    "error",
                    s.meta.id,
                    f"{status.freshness.reason}; if the source has stopped, quarantine it: "
                    "take it out of the catalog with the reason recorded",
                )

    def countries(self) -> None:
        if len(COUNTRIES) != EXPECTED_COUNTRIES:
            self.add(
                "country taxonomy",
                "error",
                "COUNTRIES",
                f"{len(COUNTRIES)} countries; the QuFin Country List has {EXPECTED_COUNTRIES}",
            )
        have = {s.meta.country for s in MacroStore(self.session).list_series()}
        empty = [c.name for c in COUNTRIES if c.iso2 not in have]
        if empty:
            self.add(
                "country data",
                "warning",
                f"{len(empty)} countries",
                "no stored series: " + ", ".join(empty),
            )
        unknown = sorted(c for c in have if c not in COUNTRY_BY_ISO2)
        if unknown:
            self.add("country taxonomy", "error", ", ".join(unknown), "series of unknown countries")


CHECKS: Sequence[str] = (
    "orphans",
    "corrupt_values",
    "date_order",
    "adjustment_tags",
    "duplicates",
    "catalog",
    "frozen",
    "countries",
)


def run(
    session: Session,
    today: date,
    *,
    fix: bool = False,
    quick: bool = False,
    on_backup: Callable[[Path], None] | None = None,
) -> DoctorReport:
    """All checks; `quick` skips the one that scans every vintage pair (for after an ingest)."""
    doctor = _Run(session, today, fix, quick)
    for name in CHECKS:
        getattr(doctor, name)()
    if doctor.backup and on_backup:
        on_backup(doctor.backup)
    return DoctorReport(doctor.findings, doctor.backup)


def format_report(report: DoctorReport) -> str:
    if not report.findings:
        return "doctor: the database is healthy"
    lines = ["check                  level    subject / detail"]
    for f in report.findings:
        mark = "FIXED" if f.fixed else f.level.upper()
        lines.append(f"{f.check:<22} {mark:<8} {f.subject}: {f.detail}")
    lines.append(
        f"doctor: {len(report.errors)} errors, {len(report.warnings)} warnings"
        + (f"; backup {report.backup}" if report.backup else "")
    )
    return "\n".join(lines)
