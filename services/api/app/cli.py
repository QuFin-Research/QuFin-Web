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
uv run python -m app.cli ingest-ons                  # UK ONS: unemployment, real GDP, core CPI
uv run python -m app.cli ingest-bis                  # BIS policy rates, exchange rates, credit
uv run python -m app.cli ingest-treasury             # Treasury debt, rates, interest
uv run python -m app.cli sync-taxonomy               # canonical codes, pillars and countries
uv run python -m app.cli build-calendar              # releases: previous, actual, next due
uv run python -m app.cli seed-benchmarks             # the 15 benchmark G20/GCC indicators
uv run python -m app.cli check-data                  # release-schedule check of every source
uv run python -m app.cli scorecard-bias              # the scorecard must show no directional bias

Ingest commands finish with the release-schedule check and exit non-zero when any series is
overdue or discontinued, so a scheduler surfaces it.
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime, timedelta

from app.connectors.bis import BisClient
from app.connectors.bls import BlsClient
from app.connectors.cftc import CftcClient
from app.connectors.ecb import EcbClient
from app.connectors.eia import EiaClient
from app.connectors.fred import FredClient
from app.connectors.imf import ImfClient
from app.connectors.oecd import OecdClient
from app.connectors.ons import OnsClient
from app.connectors.treasury import TreasuryClient
from app.core.config import get_settings
from app.data.benchmarks import BENCHMARK_SERIES
from app.data.macro_catalog import CATALOG, DEFAULT_OBSERVATION_START
from app.data.positioning_catalog import COT_CONTRACTS, DEFAULT_COT_START
from app.jobs import (
    build_calendar,
    ingest_bis,
    ingest_bls,
    ingest_cftc,
    ingest_ecb,
    ingest_eia,
    ingest_imf,
    ingest_oecd,
    ingest_ons,
    ingest_treasury,
    sync_taxonomy,
)
from app.jobs.check_data import DataCheck, check_all, check_macro, check_positioning, format_report
from app.jobs.ingest_fred import ingest, prune
from app.jobs.scorecard import bias_backtest, format_bias_report
from app.stores.db import get_engine, session_scope
from app.stores.macro import MacroStore
from app.stores.migrate import upgrade_to_head
from app.stores.raw_zone import RawZone


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
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} vintage rows" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<10} {status}")
    for series_id in removed:
        print(f"{series_id:<10} removed: no longer in the catalog")
    print()
    print(format_report(checks))
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
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised weeks" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<22} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_ecb(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "ecb"]
    with EcbClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_ecb.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<36} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_treasury(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "treasury"]
    with TreasuryClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_treasury.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<26} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_oecd(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "oecd"]
    with OecdClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_oecd.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<20} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_imf(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "imf"]
    with ImfClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_imf.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised months" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<16} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_ons(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "ons"]
    with OnsClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_ons.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<16} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_bis(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    series_ids = args.series or [s.id for s in CATALOG if s.source == "bis"]
    with BisClient(raw=_raw_zone()) as client, session_scope() as session:
        results = ingest_bis.ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<22} {status}")
    print()
    print(format_report(checks))
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
    print()
    print(format_report(checks))
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
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} new or revised periods" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<18} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _check_data(_args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    with session_scope() as session:
        checks = check_all(session, _today())
    print(format_report(checks))
    return 0 if _all_usable(checks) else 1


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
