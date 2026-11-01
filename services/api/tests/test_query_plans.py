"""Every hot query must be served by an index (rule in services/api/CLAUDE.md).

The data tables grow with every country and series; a query that scans a whole table gets
slower with each one added. Each read the pages and jobs rely on is captured here and run
through the planner: a full scan of a data table fails. Add new reads to HOT_READS.
"""

from datetime import date

import pytest
from sqlalchemy import event, text

from app.stores.macro import MacroStore
from app.stores.positioning import PositioningStore
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

DATA_TABLES = ("macro_observations", "macro_series", "cot_reports")

HOT_READS = {
    "list series": lambda s: MacroStore(s).list_series(),
    "latest view": lambda s: MacroStore(s).as_of("UNRATE", None, start=date(2025, 5, 1)),
    "as published on a date": lambda s: MacroStore(s).as_of("UNRATE", date(2026, 9, 10)),
    "revisions of a period": lambda s: MacroStore(s).revisions("UNRATE", date(2026, 8, 1)),
    "first releases, all series": lambda s: MacroStore(s).first_releases(date(2023, 11, 1)),
    "first releases, one series": lambda s: MacroStore(s).first_releases(
        date(2023, 11, 1), "UNRATE"
    ),
    "series metadata": lambda s: MacroStore(s).get_series("UNRATE"),
    "last period": lambda s: MacroStore(s).last_period("UNRATE"),
    "positioning history": lambda s: PositioningStore(s).history("088691", date(2026, 1, 1)),
    "latest positioning report": lambda s: PositioningStore(s).latest_report_date("088691"),
}


def _captured_selects(session, read):
    statements = []

    def capture(_conn, _cursor, statement, parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        read(session)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    return statements


@pytest.mark.parametrize("name", HOT_READS)
def test_hot_reads_never_scan_a_data_table(name, db_session, ingested):  # noqa: F811
    selects = _captured_selects(db_session, HOT_READS[name])
    assert selects, f"{name} ran no query"
    conn = db_session.connection()
    for statement, parameters in selects:
        plan = [
            row[-1] for row in conn.exec_driver_sql(f"EXPLAIN QUERY PLAN {statement}", parameters)
        ]
        scans = [
            step for step in plan if step.startswith("SCAN") and any(t in step for t in DATA_TABLES)
        ]
        # Listing every series reads the small series table in full by design (one row each).
        scans = [s for s in scans if not (name == "list series" and "macro_series" in s)]
        assert not scans, f"{name}: {scans} in {plan}"


def test_new_observations_are_covered_by_the_same_indexes(db_session, ingested):  # noqa: F811
    # Indexes belong to the table, so rows for any series added later are indexed on insert.
    names = {r[1] for r in db_session.execute(text("PRAGMA index_list('macro_observations')"))}
    assert {
        "ix_macro_observations_asof",
        "ix_macro_observations_asof_end",
        "ix_macro_observations_period",
    } <= names
