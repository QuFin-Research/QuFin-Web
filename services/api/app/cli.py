"""Command-line jobs.

uv run python -m app.cli migrate
uv run python -m app.cli ingest-fred            # every series in the catalog
uv run python -m app.cli ingest-fred CPIAUCSL UNRATE --start 2010-01-01
uv run python -m app.cli ingest-cftc                 # CFTC positioning, no key needed
uv run python -m app.cli ingest-eia                  # EIA weekly oil supply and demand
uv run python -m app.cli ingest-ecb                  # euro area series from the ECB
uv run python -m app.cli ingest-treasury             # Treasury debt, rates, interest
uv run python -m app.cli check-data                  # release-schedule check of every source
uv run python -m app.cli scorecard-bias              # the scorecard must show no directional bias

Ingest commands finish with the release-schedule check and exit non-zero when any series is
overdue or discontinued, so a scheduler surfaces it.
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime, timedelta

from app.connectors.cftc import CftcClient
from app.connectors.ecb import EcbClient
from app.connectors.eia import EiaClient
from app.connectors.fred import FredClient
from app.connectors.treasury import TreasuryClient
from app.core.config import get_settings
from app.data.macro_catalog import CATALOG, DEFAULT_OBSERVATION_START
from app.data.positioning_catalog import COT_CONTRACTS, DEFAULT_COT_START
from app.jobs import ingest_cftc, ingest_ecb, ingest_eia, ingest_treasury
from app.jobs.check_data import DataCheck, check_all, check_macro, check_positioning, format_report
from app.jobs.ingest_fred import ingest, prune
from app.jobs.scorecard import bias_backtest, format_bias_report
from app.stores.db import get_engine, session_scope
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

    check = sub.add_parser(
        "check-data", help="check every data source is still published on schedule"
    )
    check.set_defaults(func=_check_data)

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
