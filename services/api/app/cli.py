"""Command-line jobs.

uv run python -m app.cli migrate
uv run python -m app.cli ingest-fred            # every series in the catalog
uv run python -m app.cli ingest-fred CPIAUCSL UNRATE --start 2010-01-01
uv run python -m app.cli ingest-cftc                 # CFTC positioning, no key needed
uv run python -m app.cli ingest-bls                  # BLS series (Employment Cost Index)
uv run python -m app.cli ingest-eia                  # EIA weekly oil supply and demand
uv run python -m app.cli ingest-ecb                  # euro area series from the ECB
uv run python -m app.cli ingest-oecd                 # OECD leading indicators, confidence
uv run python -m app.cli ingest-imf                  # IMF reserves (where FRED lacks them)
uv run python -m app.cli ingest-staged               # candidate sources, loaded but never served
uv run python -m app.cli candidates                  # which candidate is timed against which pair
uv run python -m app.cli measure-candidates          # their release lags, and what rule 38 would do
uv run python -m app.cli prune-staged [--yes]        # remove staged series no candidate names
uv run python -m app.cli decide-sources [--apply]    # confirm the provisional decisions it supports
uv run python -m app.cli promote-candidate ID --as NEW --from DATE --reason TEXT  # a winner
uv run python -m app.cli ingest-eurostat             # Eurostat: industrial production, core HICP
uv run python -m app.cli ingest-worldbank           # World Bank annual indicators (new economies)
uv run python -m app.cli ingest-bcb                  # Brazil: unemployment, goods trade balance
uv run python -m app.cli ingest-singstat             # Singapore: unemployment
uv run python -m app.cli ingest-ons                  # UK ONS: unemployment, real GDP, core CPI
uv run python -m app.cli ingest-bis                  # BIS policy rates, exchange rates, credit
uv run python -m app.cli ingest-treasury             # Treasury debt, rates, interest
uv run python -m app.cli sync-taxonomy               # canonical codes, pillars and countries
uv run python -m app.cli build-calendar              # releases: previous, actual, next due
uv run python -m app.cli seed-benchmarks             # the 15 benchmark G20/GCC indicators
uv run python -m app.cli doctor [--fix]           # database health check and safe repair
uv run python -m app.cli prune-stale [--yes]         # remove series the catalog no longer lists
uv run python -m app.cli coverage-matrix --out FILE  # every country against every indicator (CSV)
uv run python -m app.cli check-data                  # release-schedule check of every source
uv run python -m app.cli source-decision ...         # record, confirm or stage a source (rule 38)
uv run python -m app.cli source-history [--country]  # which source served each pair, and when
uv run python -m app.cli catalog-version             # scorecard and catalog versions (rule 20)
uv run python -m app.cli scorecard-bias              # the scorecard must show no directional bias

Ingest commands finish with the release-schedule check and exit non-zero when any series is
overdue or discontinued, so a scheduler surfaces it.
"""

import argparse
import contextlib
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.connectors.bcb import BcbClient
from app.connectors.bis import BisClient
from app.connectors.bls import BlsClient
from app.connectors.cftc import CftcClient
from app.connectors.ecb import EcbClient
from app.connectors.eia import EiaClient
from app.connectors.eurostat import EurostatClient
from app.connectors.fred import FredClient
from app.connectors.imf import ImfClient
from app.connectors.oecd import OecdClient
from app.connectors.ons import OnsClient
from app.connectors.singstat import SingStatClient
from app.connectors.treasury import TreasuryClient
from app.connectors.worldbank import WorldBankClient
from app.core.config import get_settings
from app.data.benchmarks import BENCHMARK_SERIES
from app.data.candidates import CANDIDATES
from app.data.macro_catalog import CATALOG, DEFAULT_OBSERVATION_START
from app.data.positioning_catalog import COT_CONTRACTS, DEFAULT_COT_START
from app.data.source_baseline import BASELINE
from app.domain.versioning import SCORECARD_VERSION, catalog_version
from app.jobs import (
    build_calendar,
    coverage_matrix,
    decide_sources,
    doctor,
    ingest_bis,
    ingest_bls,
    ingest_cftc,
    ingest_ecb,
    ingest_eia,
    ingest_eurostat,
    ingest_imf,
    ingest_national,
    ingest_oecd,
    ingest_ons,
    ingest_staged,
    ingest_treasury,
    ingest_worldbank,
    measure_candidates,
    promote,
    sync_taxonomy,
)
from app.jobs.check_data import DataCheck, check_all, check_macro, check_positioning, format_report
from app.jobs.ingest_fred import ingest, prune, stale_series
from app.jobs.scorecard import bias_backtest, format_bias_report
from app.stores.candidates import CandidateStore
from app.stores.db import get_engine, session_scope
from app.stores.macro import MacroStore
from app.stores.migrate import upgrade_to_head
from app.stores.raw_zone import RawZone
from app.stores.source_decisions import CONFIRMED, PROVISIONAL, SourceStore


def _migrate(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    print("Database is at the latest migration.")
    return 0


def _ingest_fred(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.fred_api_key is None:
        print(
            "QUFIN_FRED_API_KEY is not set. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html",
            file=sys.stderr,
        )
        return 2
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "fred"]
    with (
        FredClient(
            settings.fred_api_key.get_secret_value(), settings.fred_base_url, raw=_raw_zone()
        ) as client,
        session_scope() as session,
    ):
        results = ingest(client, session, series_ids, args.start)
        removed = [] if args.series else prune(session)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} vintage rows" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<10} {status}")
    for series_id in removed:
        print(f"{series_id:<10} removed: no longer in the catalog")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_eia(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.eia_api_key is None:
        print(
            "QUFIN_EIA_API_KEY is not set. Get a free key at https://www.eia.gov/opendata/",
            file=sys.stderr,
        )
        return 2
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "eia"]
    with (
        EiaClient(
            settings.eia_api_key.get_secret_value(), settings.eia_base_url, raw=_raw_zone()
        ) as client,
        session_scope() as session,
    ):
        results = ingest_eia.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised weeks" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<22} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_ecb(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "ecb"]
    with EcbClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_ecb.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<36} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_treasury(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "treasury"]
    with TreasuryClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_treasury.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<26} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_oecd(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "oecd"]
    with OecdClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_oecd.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<20} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_imf(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "imf"]
    with ImfClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_imf.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<16} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_staged(args: argparse.Namespace) -> int:
    """Load the candidate sources without serving them (rule 38). Reported, never a failed run."""
    upgrade_to_head(get_engine())
    chosen = [
        c
        for c in CANDIDATES
        if args.source in (None, c.source) and (not args.only or c.id in args.only)
    ]
    if not chosen:
        print("no candidates: nothing is staged (rule 38, Bloc aggregator first)")
        return 0
    settings = get_settings()
    needed = {c.source for c in chosen}
    if "fred" in needed and settings.fred_api_key is None:
        print("QUFIN_FRED_API_KEY is not set: FRED candidates cannot be loaded", file=sys.stderr)
        return 2
    with contextlib.ExitStack() as stack:
        clients: dict[str, object] = {}
        if "imf" in needed:
            clients["imf"] = stack.enter_context(ImfClient(raw=_raw_zone()))
        if "fred" in needed and settings.fred_api_key is not None:
            clients["fred"] = stack.enter_context(
                FredClient(
                    settings.fred_api_key.get_secret_value(),
                    settings.fred_base_url,
                    raw=_raw_zone(),
                )
            )
        if "eurostat" in needed:
            clients["eurostat"] = stack.enter_context(EurostatClient(raw=_raw_zone()))
        if "oecd" in needed:
            clients["oecd"] = stack.enter_context(OecdClient(raw=_raw_zone()))
        if "bis" in needed:
            clients["bis"] = stack.enter_context(BisClient(raw=_raw_zone()))
        if "bls" in needed:
            bls_key = settings.bls_api_key
            clients["bls"] = stack.enter_context(
                BlsClient(bls_key.get_secret_value() if bls_key else None, raw=_raw_zone())
            )
        session = stack.enter_context(session_scope())
        results = ingest_staged.ingest(clients, session, chosen, args.start)
    for r in results:
        status = (
            f"{r.rows} new or revised observations"
            if r.error is None
            else f"FAILED: {r.error}"
        )
        print(f"{r.series_id:<22} {status}")
    failed = sum(r.error is not None for r in results)
    print(f"staged: {len(results) - failed} of {len(results)} candidates loaded")
    return 0 if not failed else 1


def _prune_staged(args: argparse.Namespace) -> int:
    """Remove staged series no candidate names any more, after a backup. Needs --yes."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        stale = ingest_staged.stale_staged(session)
        if not stale:
            print("no stale staged series")
            return 0
        print(f"staged series no candidate names: {len(stale)}")
        if not args.yes:
            print("nothing removed; run again with --yes to back up the database and remove them")
            return 1
        backup = doctor.backup_database(session)
        removed = ingest_staged.prune_staged(session, stale)
        print(f"removed {removed} staged series; backup: {backup}")
    return 0


def _candidates(_args: argparse.Namespace) -> int:
    """Which candidate serves which pair, and what has been seen of it."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        store, sightings = MacroStore(session), CandidateStore(session)
        stored = {s.meta.id: s for s in store.list_series(("staged",))}
        print(f"{'candidate':<22} {'pair':<22} {'serves':<20} {'last period':<12} first reads")
        for c in CANDIDATES:
            row = stored.get(c.id)
            last = row.last_period.isoformat()[:7] if row and row.last_period else "not loaded"
            reads = len(sightings.measurable(c.id)) if row else 0
            print(f"{c.id:<22} {c.country + ' ' + c.concept:<22} {c.serves:<20} {last:<12} {reads}")
    return 0


def _measure_candidates(_args: argparse.Namespace) -> int:
    """Rule 38: each candidate's lag against the series that serves its pair. Records nothing."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        measured = measure_candidates.measure_all(session, CANDIDATES)
    print(
        f"{'candidate':<22} {'serves':<16} {'served':>6} {'candidate':>9}  "
        f"{'earlier (served/cand/level)':<27} {'verdict':<18} action"
    )
    for m in measured:
        if m.served_median is None:
            print(f"{m.candidate_id:<22} {m.serves:<16} no period published since staging yet")
            continue
        split = f"{m.served_wins}/{m.candidate_wins}/{m.level}"
        plus = "+" if m.bounded else " "  # at least: one side had not shown a period yet
        print(
            f"{m.candidate_id:<22} {m.serves:<16} {m.served_median:>5}d "
            f"{m.candidate_median:>7}d{plus} "
            f"{split:<27} {m.verdict:<18} {m.recommendation}"
        )
    waiting = sum(m.served_median is None for m in measured)
    print(f"{len(measured) - waiting} of {len(measured)} measured; {waiting} waiting for a release")
    return 0


def _decide_sources(args: argparse.Namespace) -> int:
    """Rule 38: what the measurement means for each provisional decision. --apply confirms only."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        outcomes = decide_sources.plan(session, CANDIDATES)
        print(f"{'candidate':<22} {'pair':<22} {'decision':<12} {'action':<12} why")
        for o in outcomes:
            c = o.candidate
            pair = f"{c.country} {c.concept}"
            print(f"{c.id:<22} {pair:<22} {o.status or '-':<12} {o.action:<12} {o.why}")
        counts = {a: sum(o.action == a for o in outcomes) for a in decide_sources.ACTIONS}
        print(", ".join(f"{n} {a}" for a, n in counts.items() if n))
        if args.apply:
            done = decide_sources.apply(session, outcomes)
            print(
                f"confirmed {len(done)} decisions in this database; to keep them for every "
                "database set status to confirmed in app/data/source_baseline.py"
            )
        elif counts[decide_sources.CONFIRM]:
            print("nothing recorded; run again with --apply to confirm them")
    return 0


def _promote_candidate(args: argparse.Namespace) -> int:
    """Move a winning staged candidate into the catalog series a reviewed pull request added."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        try:
            done = promote.promote(
                session, args.candidate, args.series, args.effective_from, reason=args.reason
            )
        except promote.PromotionError as exc:
            print(f"refused: {exc}")
            return 2
    print(
        f"{done.candidate_id} -> {done.series_id}: {done.observations} observations and "
        f"{done.sightings} first reads moved; {done.retired} is retired from {args.effective_from}"
    )
    return 0


def _ingest_ons(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "ons"]
    with OnsClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_ons.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<16} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_eurostat(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "eurostat"]
    with EurostatClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_eurostat.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<18} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_worldbank(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "worldbank"]
    with WorldBankClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_worldbank.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised years" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<14} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_bcb(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "bcb"]
    with BcbClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_national.ingest_bcb(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<14} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_singstat(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "singstat"]
    with SingStatClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_national.ingest_singstat(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised quarters" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<14} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_bis(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "bis"]
    with BisClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_bis.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<22} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_cftc(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    symbols = [s.upper() for s in args.symbols] or [c.symbol for c in COT_CONTRACTS]
    with CftcClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_cftc.ingest(client, session, symbols, args.start, args.full)
        checks = check_positioning(session, _today())
    for r in results:
        status = f"{r.rows} weekly reports" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.symbol:<8} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_bls(args: argparse.Namespace) -> int:
    settings = get_settings()
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "bls"]
    bls_key = getattr(settings, "bls_api_key", None)
    api_key = bls_key.get_secret_value() if bls_key is not None else None
    if api_key is None:
        print(
            "Note: no BLS registration key; anonymous access is capped at 25 queries/day "
            "and 10 years per request. Get a free key at "
            "https://data.bls.gov/registrationEngine/",
            file=sys.stderr,
        )
    with BlsClient(api_key=api_key, raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_bls.ingest(client, session, series_ids, args.start)
        checks = _release_check(session)
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<18} {status}")
    _finish_report(checks)
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


DEFER_CHECKS_ENV = "QUFIN_DEFER_RELEASE_CHECK"


def _deferred() -> bool:
    """True when the data refresh job runs this command: it runs one release check at the end of
    its run instead of one (about three minutes) after every source."""
    return os.environ.get(DEFER_CHECKS_ENV) == "1"


def _release_check(session: Session) -> list[DataCheck]:
    return [] if _deferred() else check_macro(session, _today())


def _finish_report(checks: list[DataCheck]) -> None:
    """What every ingest ends with (rules 2 and 36): the release report and the doctor line."""
    if _deferred():
        return
    print()
    print(format_report(checks))
    _doctor_summary()


def _doctor_summary() -> None:
    """One line after every ingest (Rule 36): the quick checks, without any repair."""
    with session_scope() as session:
        report = doctor.run(session, _today(), quick=True)
    print(
        f"doctor: {len(report.errors)} errors, {len(report.warnings)} warnings "
        "(uv run python -m app.cli doctor for the list)"
    )


def _prune_stale(args: argparse.Namespace) -> int:
    """Remove the series the catalog no longer lists, after a backup. The doctor only reports them
    (rule 36); removing data is a decision, so it needs --yes."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        stale = stale_series(MacroStore(session))
        if not stale:
            print("no stale series")
            return 0
        print("stale series: " + ", ".join(stale))
        if not args.yes:
            print("nothing removed; run again with --yes to back up the database and remove them")
            return 1
        backup = doctor.backup_database(session)
        removed = prune(session)
        print(f"removed {len(removed)} series; backup: {backup}")
    return 0


def _doctor(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        report = doctor.run(session, _today(), fix=args.fix, quick=args.quick)
    print(doctor.format_report(report))
    if args.gaps:
        with session_scope() as session:
            print()
            print(doctor.format_gaps(doctor.unpopulated_pairs(session)))
    return 0 if not report.errors else 1


def _coverage_matrix(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        cells = coverage_matrix.build(session, _today())
    print(coverage_matrix.format_summary(coverage_matrix.summarize(cells)))
    if args.out:
        coverage_matrix.write_csv(cells, Path(args.out))
        print(f"coverage matrix: wrote {len(cells)} rows to {args.out}")
    return 0


def _discover(args: argparse.Namespace) -> int:
    """The discovery probe (rule 34): what each source publishes, against what QuFin holds. It
    stores nothing."""
    from app.connectors.bis import BisClient
    from app.connectors.eurostat import EurostatClient
    from app.connectors.oecd import OecdClient
    from app.jobs import discover

    upgrade_to_head(get_engine())
    with (
        OecdClient(raw=_raw_zone()) as oecd,
        EurostatClient(raw=_raw_zone()) as eurostat,
        BisClient(raw=_raw_zone()) as bis,
        session_scope() as session,
    ):
        findings = discover.sweep(
            {"oecd": oecd, "eurostat": eurostat, "bis": bis}, session, args.concept, _today()
        )
    print(discover.format_report(findings))
    if args.out:
        discover.write_csv(findings, Path(args.out))
        print(f"wrote {len(findings)} rows to {args.out}")
    return 0


def _check_data(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        checks = check_all(session, _today())
    print(format_report(checks))
    return 0 if _all_usable(checks) else 1


def _source_decision(args: argparse.Namespace) -> int:
    """Rule 38: record that a series serves a pair from a date, confirm a provisional decision,
    or stage a candidate. A change retires the previous series (rule 16)."""
    upgrade_to_head(get_engine())
    with session_scope() as session:
        sources = SourceStore(session)
        if args.baseline:
            applied = confirmed = 0
            for b in BASELINE:
                history = sources.history(b.country, b.concept)
                if history and history[-1].effective_to is None:
                    if history[-1].series_id == b.series_id:
                        if b.status == CONFIRMED and history[-1].status != CONFIRMED:
                            sources.confirm(b.country, b.concept)
                            confirmed += 1
                        continue
                elif not history and b.predecessor is not None:
                    p = b.predecessor
                    sources.decide(
                        b.country,
                        b.concept,
                        p.series_id,
                        p.source,
                        p.effective_from,
                        reason=p.reason,
                    )
                sources.decide(
                    b.country,
                    b.concept,
                    b.series_id,
                    b.source,
                    b.effective_from,
                    reason=b.reason,
                    status=b.status,
                )
                applied += 1
            print(
                f"baseline: {applied} decisions recorded, {len(BASELINE) - applied} already there, "
                f"{confirmed} confirmed"
            )
            return 0
        if args.stage:
            sources.stage(args.stage)
            print(f"staged {args.stage}: loaded and timed, never served or scored")
            return 0
        if args.confirm:
            sources.confirm(args.country, args.concept)
            print(f"confirmed the source of {args.country} {args.concept}")
            return 0
        if not (args.series and args.source and args.reason):
            print("a decision needs --series, --source and --reason")
            return 2
        try:
            decision = sources.decide(
                args.country,
                args.concept,
                args.series,
                args.source,
                args.effective_from or _today(),
                reason=args.reason,
                status=PROVISIONAL if args.provisional else CONFIRMED,
            )
        except ValueError as exc:
            print(f"refused: {exc}")
            return 2
        print(f"{decision.country} {decision.concept}: {decision.series_id} ({decision.status})")
        print(f"from {decision.effective_from}; catalog version {catalog_version(session)}")
    return 0


def _source_history(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        decisions = [
            d for d in SourceStore(session).all() if not args.country or d.country == args.country
        ]
    for d in decisions:
        until = d.effective_to.isoformat() if d.effective_to else "now"
        print(
            f"{d.country} {d.concept}: {d.series_id} [{d.source}] "
            f"{d.effective_from} -> {until} ({d.status}) {d.reason}"
        )
    if not decisions:
        print("no source decisions: every pair is served by its catalog series")
    return 0


def _catalog_version(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        print(f"scorecard {SCORECARD_VERSION}, catalog {catalog_version(session)}")
    return 0


def _scorecard_bias(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        report = bias_backtest(session, args.start, args.end)
    print(format_bias_report(report))
    return 0 if report.passed else 1


def _sync_taxonomy(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        result = sync_taxonomy.sync(session)
    print(f"{result.countries} countries; {result.series} series coded, {result.changed} changed")
    if result.uncoded:
        print(f"NO CODE for {len(result.uncoded)} series: {', '.join(result.uncoded)}")
    return 1 if result.uncoded else 0


def _build_calendar(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        result = build_calendar.build(session, _today())
    print(f"calendar: {result.released} released events, {result.scheduled} scheduled")
    return 0


def _seed_benchmarks(_args: argparse.Namespace) -> int:
    """Code the benchmark indicators and show each one's latest real value."""
    upgrade_to_head(get_engine())
    missing = 0
    with session_scope() as session:
        sync_taxonomy.sync(session)
        store = MacroStore(session)
        for series_id in BENCHMARK_SERIES:
            meta = store.get_series(series_id)
            last = store.last_period(series_id)
            if meta is None or last is None:
                print(f"NOT LOADED  {series_id}: run its ingest command first")
                missing += 1
                continue
            value = store.as_of(series_id, None, start=last)[-1].value
            print(f"{meta.canonical_code:<48} {last}  {value}  {meta.units}")
    return 1 if missing else 0


def _raw_zone() -> RawZone | None:
    raw_dir = get_settings().raw_dir
    return RawZone(raw_dir) if raw_dir else None


def _today() -> date:
    return datetime.now(UTC).date()


def _all_usable(checks: list[DataCheck]) -> bool:
    return all(c.status.freshness.usable for c in checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="apply database migrations").set_defaults(func=_migrate)

    fred = sub.add_parser("ingest-fred", help="ingest FRED/ALFRED series with all vintages")
    fred.add_argument("series", nargs="*", help="series IDs (default: the whole catalog)")
    fred.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first observation date (default {DEFAULT_OBSERVATION_START})",
    )
    fred.set_defaults(func=_ingest_fred)

    eia = sub.add_parser("ingest-eia", help="ingest EIA weekly petroleum (oil) series")
    eia.add_argument("series", nargs="*", help="EIA series ids (default: every catalog EIA series)")
    eia.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first week to load (default {DEFAULT_OBSERVATION_START})",
    )
    eia.set_defaults(func=_ingest_eia)

    ecb = sub.add_parser("ingest-ecb", help="ingest euro area series from the ECB Data Portal")
    ecb.add_argument("series", nargs="*", help="series ids (default: every ECB series)")
    ecb.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first period to load (default {DEFAULT_OBSERVATION_START})",
    )
    ecb.set_defaults(func=_ingest_ecb)

    treasury = sub.add_parser("ingest-treasury", help="ingest Treasury Fiscal Data series")
    treasury.add_argument("series", nargs="*", help="series ids (default: every Treasury series)")
    treasury.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first period to load (default {DEFAULT_OBSERVATION_START})",
    )
    treasury.set_defaults(func=_ingest_treasury)

    oecd = sub.add_parser("ingest-oecd", help="ingest OECD leading indicators and confidence")
    oecd.add_argument("series", nargs="*", help="series ids (default: every OECD series)")
    oecd.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first month to load (default {DEFAULT_OBSERVATION_START})",
    )
    oecd.set_defaults(func=_ingest_oecd)

    imf = sub.add_parser("ingest-imf", help="ingest IMF series (reserves)")
    imf.add_argument("series", nargs="*", help="series ids (default: every IMF series)")
    imf.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first month to load (default {DEFAULT_OBSERVATION_START})",
    )
    imf.set_defaults(func=_ingest_imf)

    staged = sub.add_parser(
        "ingest-staged", help="load candidate sources without serving them (rule 38)"
    )
    staged.add_argument(
        "--source", choices=["imf", "fred", "bls", "eurostat", "oecd", "bis"], default=None
    )
    staged.add_argument("--start", type=date.fromisoformat, default=DEFAULT_OBSERVATION_START)
    staged.add_argument(
        "--only",
        action="append",
        metavar="CANDIDATE",
        help="load only this candidate id (repeatable), e.g. after a supplier's rate limit",
    )
    staged.set_defaults(func=_ingest_staged)
    sub.add_parser(
        "candidates",
        help="the candidate sources, the pair each is timed against, and what was read",
    ).set_defaults(func=_candidates)
    pruned = sub.add_parser(
        "prune-staged", help="remove staged series no candidate names any more (backs up first)"
    )
    pruned.add_argument("--yes", action="store_true", help="really remove them")
    pruned.set_defaults(func=_prune_staged)
    sub.add_parser(
        "measure-candidates",
        help="each candidate release lag against the series it is timed against",
    ).set_defaults(func=_measure_candidates)
    decide = sub.add_parser(
        "decide-sources", help="what the measurement means for each provisional decision"
    )
    decide.add_argument("--apply", action="store_true", help="confirm the decisions it supports")
    decide.set_defaults(func=_decide_sources)
    promo = sub.add_parser(
        "promote-candidate", help="move a winning staged candidate into its new catalog series"
    )
    promo.add_argument("candidate", help="the staged candidate id, e.g. CAND_IMF_CPI_DEU")
    promo.add_argument("--as", dest="series", required=True, help="the new catalog series id")
    promo.add_argument("--from", dest="effective_from", type=date.fromisoformat, required=True)
    promo.add_argument("--reason", required=True, help="the measurement, per rule 38")
    promo.set_defaults(func=_promote_candidate)

    ons = sub.add_parser("ingest-ons", help="ingest UK ONS series (unemployment, GDP, core CPI)")
    ons.add_argument("series", nargs="*", help="series ids (default: every ONS series)")
    ons.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help="first period to load (default: each series' own history, 1990 for new series)",
    )
    ons.set_defaults(func=_ingest_ons)

    bis = sub.add_parser(
        "ingest-bis", help="ingest BIS policy rates, effective exchange rates and credit-to-GDP"
    )
    bis.add_argument("series", nargs="*", help="series ids (default: every BIS series)")
    bis.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first period to load (default {DEFAULT_OBSERVATION_START})",
    )
    bis.set_defaults(func=_ingest_bis)

    cftc = sub.add_parser("ingest-cftc", help="ingest CFTC Commitments of Traders reports")
    cftc.add_argument("symbols", nargs="*", help="QuFin symbols (default: every mapped asset)")
    cftc.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_COT_START,
        help=f"first report date (default {DEFAULT_COT_START})",
    )
    cftc.add_argument("--full", action="store_true", help="re-read all history, not just new weeks")
    cftc.set_defaults(func=_ingest_cftc)

    estat = sub.add_parser("ingest-eurostat", help="ingest Eurostat series (production, core HICP)")
    estat.add_argument("series", nargs="*", help="series ids (default: every Eurostat series)")
    estat.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help="first month to load (default: 1990, or the source's own start)",
    )
    estat.set_defaults(func=_ingest_eurostat)

    wb = sub.add_parser("ingest-worldbank", help="ingest World Bank annual indicators")
    wb.add_argument("series", nargs="*", help="series ids (default: every World Bank series)")
    wb.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help="first year to load (default: 1990, or the source's own start)",
    )
    wb.set_defaults(func=_ingest_worldbank)

    for name, func, label in (
        ("ingest-bcb", _ingest_bcb, "Brazil: unemployment and goods trade balance (BCB SGS)"),
        ("ingest-singstat", _ingest_singstat, "Singapore: unemployment (SingStat)"),
    ):
        nat = sub.add_parser(name, help=f"ingest {label}")
        nat.add_argument(
            "series", nargs="*", help="series ids (default: every series of the source)"
        )
        nat.add_argument(
            "--start",
            type=date.fromisoformat,
            default=DEFAULT_OBSERVATION_START,
            help="first period to load (default: 1990, or the source's own start)",
        )
        nat.set_defaults(func=func)

    stale = sub.add_parser(
        "prune-stale", help="remove series the catalog no longer lists (backs up first)"
    )
    stale.add_argument("--yes", action="store_true", help="really remove them")
    stale.set_defaults(func=_prune_stale)
    doc = sub.add_parser("doctor", help="check the database's health; --fix repairs what is safe")
    doc.add_argument("--fix", action="store_true", help="repair (a backup is taken first)")
    doc.add_argument("--quick", action="store_true", help="skip the vintage overlap scan")
    doc.add_argument(
        "--gaps", action="store_true", help="list unpopulated pairs with tier 3 portals"
    )
    doc.set_defaults(func=_doctor)

    matrix = sub.add_parser(
        "coverage-matrix", help="every country against every indicator, from the database"
    )
    matrix.add_argument("--out", help="write the full matrix to this CSV file")
    matrix.set_defaults(func=_coverage_matrix)
    probe = sub.add_parser(
        "discover", help="probe the sources for indicators QuFin lacks (rule 34); stores nothing"
    )
    probe.add_argument("--concept", action="append", help="limit to this indicator (repeatable)")
    probe.add_argument("--out", help="write every finding to this CSV file")
    probe.set_defaults(func=_discover)

    bls = sub.add_parser("ingest-bls", help="ingest BLS series (Employment Cost Index)")
    bls.add_argument("series", nargs="*", help="series ids (default: every BLS series)")
    bls.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_OBSERVATION_START,
        help=f"first period to load (default {DEFAULT_OBSERVATION_START})",
    )
    bls.set_defaults(func=_ingest_bls)

    check = sub.add_parser(
        "check-data", help="check every data source is still published on schedule"
    )
    check.set_defaults(func=_check_data)

    decide = sub.add_parser(
        "source-decision", help="record, confirm or stage the source of a country-indicator pair"
    )
    decide.add_argument("--country", help="ISO 3166 alpha-2 of the pair, e.g. PT")
    decide.add_argument("--concept", help="the indicator concept key, e.g. consumer_prices")
    decide.add_argument("--series", help="the series that serves the pair from the date")
    decide.add_argument("--source", help="the source of that series, e.g. eurostat")
    decide.add_argument("--reason", help="why: the candidates measured, per rule 38")
    decide.add_argument("--from", dest="effective_from", type=date.fromisoformat)
    decide.add_argument("--provisional", action="store_true", help="first choice for a new pair")
    decide.add_argument("--confirm", action="store_true", help="confirm the provisional decision")
    decide.add_argument(
        "--baseline", action="store_true", help="record the decisions made before the store"
    )
    decide.add_argument("--stage", metavar="SERIES", help="mark a candidate series as staged")
    decide.set_defaults(func=_source_decision)
    history = sub.add_parser("source-history", help="which source served each pair, and when")
    history.add_argument("--country")
    history.set_defaults(func=_source_history)
    sub.add_parser(
        "catalog-version", help="the scorecard and catalog versions scores are computed with"
    ).set_defaults(func=_catalog_version)
    sub.add_parser(
        "sync-taxonomy", help="set every series' canonical code and pillar; refresh countries"
    ).set_defaults(func=_sync_taxonomy)
    sub.add_parser(
        "build-calendar", help="build the economic calendar from the point-in-time store"
    ).set_defaults(func=_build_calendar)
    sub.add_parser(
        "seed-benchmarks", help="code the 15 benchmark G20/GCC indicators and show their values"
    ).set_defaults(func=_seed_benchmarks)

    bias = sub.add_parser(
        "scorecard-bias",
        help="compare the scorecard users saw each month with complete information",
    )
    bias.add_argument("--start", type=date.fromisoformat, default=date(2012, 1, 1))
    bias.add_argument(
        "--end",
        type=date.fromisoformat,
        default=None,
        help="last month to test (default: four months ago, so complete data exists)",
    )
    bias.set_defaults(func=_scorecard_bias)

    args = parser.parse_args(argv)
    if getattr(args, "func", None) is _scorecard_bias and args.end is None:
        args.end = _today() - timedelta(days=125)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
