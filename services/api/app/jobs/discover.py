"""The discovery probe (rule 34): which source publishes which indicator for which economy.

It asks each source in `app/data/probes.py`, compares the answer with what QuFin holds (the
coverage matrix) and reports. It stores nothing: staging and serving are decisions for a reviewed
pull request (rules 26, 34 and 38). An economy the sweep did not reach within the time budget is
`pending` (never failed) for the next run.

For an economy Eurostat serves, a Eurostat answer is the one that would serve the pair (rule 38,
*Bloc aggregator first*), whatever any other source shows.
"""

import csv
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.eurostat import EurostatError
from app.connectors.sdmx import SdmxError, parse_all
from app.data.gap_ids import HICP_GEO
from app.data.probes import PROBES, Probe
from app.data.taxonomy import COUNTRIES, COUNTRY_BY_ISO3
from app.domain.source_selection import bloc_aggregator_of
from app.jobs import coverage_matrix

PUBLISHED, ABSENT, PENDING, FAILED = "published", "absent", "pending", "failed"
HELD_STATUSES = ("HAVE", "OVERDUE")
PROBE_START_MONTHS = 8  # a recent window is enough to see the latest period
CURRENT_WITHIN = timedelta(days=150)  # latest period no older than this: publishing on schedule
CURRENT_WITHIN_QUARTERLY = timedelta(days=345)  # a quarter dated at its start, plus its lag
SWEEP_BUDGET_SECONDS = 21600  # DISCOVERY_SWEEP_TIME_BUDGET_SECONDS (Part 0, 0.2)
_ISO3_BY_ISO2 = {c.iso2: c.iso3 for c in COUNTRIES}


@dataclass(frozen=True)
class Finding:
    concept: str
    source: str
    iso3: str
    status: str  # published, absent, pending or failed
    last_period: date | None = None
    current: bool = False  # published and not stale
    held: bool = False  # QuFin already holds the pair
    bloc_first: bool = False  # Eurostat would serve it, whatever any other source shows
    detail: str = ""


def _iso3_of(area: str) -> str | None:
    if area in COUNTRY_BY_ISO3:
        return area
    if area in _ISO3_BY_ISO2:  # the BIS names an economy by its two-letter code
        return _ISO3_BY_ISO2[area]
    if area == "XM":  # the BIS's euro area
        return _ISO3_BY_ISO2["EA"]
    if area.startswith("EA"):  # the OECD's EA20 and the like
        return _ISO3_BY_ISO2["EA"]
    return None


def _window(today: date, months_back: int = 0) -> date:
    months = today.year * 12 + today.month - 1 - (months_back or PROBE_START_MONTHS)
    return date(months // 12, months % 12 + 1, 1)


def held_pairs(session: Session, today: date) -> dict[str, set[str]]:
    """Concept -> ISO3 of the economies QuFin holds a series for."""
    held: dict[str, set[str]] = defaultdict(set)
    for cell in coverage_matrix.build(session, today):
        if cell.status in HELD_STATUSES:
            held[cell.concept_key].add(cell.iso3)
    return held


def _finding(
    probe: Probe,
    iso3: str,
    held: Mapping[str, set[str]],
    last: date | None,
    today: date,
    status: str | None = None,
    detail: str = "",
) -> Finding:
    iso2 = COUNTRY_BY_ISO3[iso3].iso2
    return Finding(
        probe.concept,
        probe.source,
        iso3,
        status or (PUBLISHED if last else ABSENT),
        last,
        current=bool(
            last and today - last <= (CURRENT_WITHIN_QUARTERLY if probe.months else CURRENT_WITHIN)
        ),
        held=iso3 in held.get(probe.concept, set()),
        bloc_first=probe.source == "eurostat" and bloc_aggregator_of(iso2) == "eurostat",
        detail=detail,
    )


def probe_oecd(
    client: Any, probe: Probe, held: Mapping[str, set[str]], today: date
) -> list[Finding]:
    """One wildcard request answers for every economy the dataflow covers."""
    try:
        series = parse_all(
            probe.flow, probe.key, client._data(probe.flow, probe.key, _window(today, probe.months))
        )
    except SdmxError as exc:
        if "404" not in str(exc):  # the OECD answers 404 when nothing matches
            return [_finding(probe, c.iso3, held, None, today, FAILED, str(exc)) for c in COUNTRIES]
        series = []
    last: dict[str, date] = {}
    for s in series:
        iso3 = _iso3_of(s.dimensions.get("REF_AREA", ""))
        periods = [p for p, v in s.observations if v is not None]
        if iso3 and periods:
            last[iso3] = max([*periods, last.get(iso3, date.min)])
    return [_finding(probe, c.iso3, held, last.get(c.iso3), today) for c in COUNTRIES]


def probe_bis(
    client: Any, probe: Probe, held: Mapping[str, set[str]], today: date
) -> list[Finding]:
    """One wildcard request answers for every economy the dataflow covers."""
    try:
        series = client.many(probe.flow, probe.key, _window(today, probe.months), probe.version)
    except SdmxError as exc:
        return [_finding(probe, c.iso3, held, None, today, FAILED, str(exc)) for c in COUNTRIES]
    last: dict[str, date] = {}
    for s in series:
        iso3 = _iso3_of(s.dimensions.get(probe.area_dimension, ""))
        periods = [p for p, v in s.observations if v is not None]
        if iso3 and periods:
            last[iso3] = max([*periods, last.get(iso3, date.min)])
    return [_finding(probe, c.iso3, held, last.get(c.iso3), today) for c in COUNTRIES]


def probe_eurostat(
    client: Any, probe: Probe, held: Mapping[str, set[str]], today: date, deadline: float
) -> list[Finding]:
    """One request per economy Eurostat serves; the other economies are not its to serve."""
    found = []
    for iso2, geo in HICP_GEO.items():
        iso3 = _ISO3_BY_ISO2.get(iso2)
        if iso3 is None:
            continue
        if time.monotonic() > deadline:
            found.append(_finding(probe, iso3, held, None, today, PENDING))
            continue
        try:
            extra = {"quarterly": True} if probe.quarterly else {}
            series = client.series(
                probe.dataset, {**probe.filters, "geo": geo}, _window(today, probe.months), **extra
            )
        except EurostatError as exc:
            absent = "no observations" in str(exc) or "no data" in str(exc)
            found.append(
                _finding(
                    probe, iso3, held, None, today,
                    ABSENT if absent else FAILED, "" if absent else str(exc),
                )
            )  # fmt: skip
            continue
        found.append(_finding(probe, iso3, held, series.observations[-1][0], today))
    return found


def sweep(
    clients: Mapping[str, Any],
    session: Session,
    concepts: Iterable[str] | None = None,
    today: date | None = None,
    budget: float = SWEEP_BUDGET_SECONDS,
    probes: Iterable[Probe] = PROBES,
) -> list[Finding]:
    today = today or datetime.now(UTC).date()
    wanted = set(concepts) if concepts else None
    held = held_pairs(session, today)
    deadline = time.monotonic() + budget
    findings: list[Finding] = []
    for probe in probes:
        client = clients.get(probe.source)
        if client is None or (wanted and probe.concept not in wanted):
            continue
        if probe.source == "oecd":
            findings += probe_oecd(client, probe, held, today)
        elif probe.source == "bis":
            findings += probe_bis(client, probe, held, today)
        else:
            findings += probe_eurostat(client, probe, held, today, deadline)
    return findings


def summarize(findings: Iterable[Finding]) -> dict[str, dict[str, dict[str, int]]]:
    """Per concept and source: how many economies publish currently, are behind, are absent, are
    pending or failed, and how many of the current ones QuFin does not hold yet."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for f in findings:
        row = out.setdefault(f.concept, {}).setdefault(
            f.source, dict.fromkeys(("current", "behind", "absent", "pending", "failed", "new"), 0)
        )
        if f.status == PUBLISHED:
            row["current" if f.current else "behind"] += 1
            row["new"] += f.current and not f.held
        else:
            row[f.status] += 1
    return out


def write_csv(findings: Iterable[Finding], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([f.name for f in fields(Finding)])
        for f in findings:
            writer.writerow([getattr(f, x.name) for x in fields(Finding)])


def format_report(findings: list[Finding]) -> str:
    lines = ["discovery probe (nothing was stored)"]
    for concept, sources in summarize(findings).items():
        lines.append(f"\n{concept}")
        lines.append(f"  {'source':<10}{'current':>8}{'behind':>8}{'absent':>8}{'new':>6}  note")
        for source, r in sources.items():
            note = []
            if r["pending"]:
                note.append(f"{r['pending']} pending")
            if r["failed"]:
                note.append(f"{r['failed']} failed")
            lines.append(
                f"  {source:<10}{r['current']:>8}{r['behind']:>8}{r['absent']:>8}{r['new']:>6}"
                f"  {', '.join(note)}"
            )
    return "\n".join(lines)
