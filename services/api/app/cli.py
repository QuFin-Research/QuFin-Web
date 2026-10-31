"""Command-line jobs.

uv run python -m app.cli migrate
uv run python -m app.cli ingest-fred            # every series in the catalog
uv run python -m app.cli ingest-fred CPIAUCSL UNRATE --start 2010-01-01
uv run python -m app.cli ingest-cftc                 # CFTC positioning, no key needed
uv run python -m app.cli check-data                  # release-schedule check of every source

Ingest commands finish with the release-schedule check and exit non-zero when any series is
overdue or discontinued, so a scheduler surfaces it.
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime

from app.connectors.cftc import CftcClient
from app.connectors.fred import FredClient
from app.core.config import get_settings
from app.data.macro_catalog import CATALOG, DEFAULT_OBSERVATION_START
from app.data.positioning_catalog import COT_CONTRACTS, DEFAULT_COT_START
from app.jobs import ingest_cftc
from app.jobs.check_data import DataCheck, check_all, check_macro, check_positioning, format_report
from app.jobs.ingest_fred import ingest
from app.stores.db import get_engine, session_scope
from app.stores.migrate import upgrade_to_head


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
    series_ids = args.series or [s.id for s in CATALOG]
    with (
        FredClient(settings.fred_api_key.get_secret_value(), settings.fred_base_url) as client,
        session_scope() as session,
    ):
        results = ingest(client, session, series_ids, args.start)
        checks = check_macro(session, _today())
    for r in results:
        status = f"{r.rows} vintage rows" if r.error is None else f"FAILED: {r.error}"
        print(f"{r.series_id:<10} {status}")
    print()
    print(format_report(checks))
    return 0 if all(r.error is None for r in results) and _all_usable(checks) else 1


def _ingest_cftc(args: argparse.Namespace) -> int:
    upgrade_to_head(get_engine())
    symbols = [s.upper() for s in args.symbols] or [c.symbol for c in COT_CONTRACTS]
    with CftcClient() as client, session_scope() as session:
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

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
