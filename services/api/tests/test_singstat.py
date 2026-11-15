"""SingStat Table Builder connector and ingest: parsing, refusal stop, dating, catalog."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date

import httpx
import pytest

from app.connectors.base import USER_AGENT
from app.connectors.singstat import SingStatClient, SingStatError, parse_quarter
from app.data.gap_ids import HISTORY_START, SINGSTAT_BY_ID
from app.data.macro_catalog import BY_ID
from app.data.national_calendar import singapore_quarterly_release
from app.jobs import ingest_national
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


def table(rows):
    return {"Data": {"title": "Unemployment", "row": rows}}


def row(no, *columns):
    return {
        "seriesNo": no,
        "rowText": f"series {no}",
        "uoM": "Per Cent",
        "columns": [{"key": k, "value": v} for k, v in columns],
    }


def client_for(handler):
    return SingStatClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


def test_quarters_are_read_as_their_first_day():
    assert parse_quarter("2026 3Q") == date(2026, 7, 1)
    assert parse_quarter("1992 1Q") == date(1992, 1, 1)
    with pytest.raises(SingStatError):
        parse_quarter("2026")


def test_the_wanted_row_is_read_from_the_start_and_blanks_are_skipped():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers["user-agent"]))
        return httpx.Response(
            200,
            json=table(
                [
                    row("1", ("2024 4Q", "2.0"), ("2025 1Q", ""), ("2025 2Q", "2.1")),
                    row("2", ("2025 2Q", "9.9")),
                ]
            ),
        )

    data = client_for(handler).series("M182342", "1", date(2025, 1, 1))
    assert data == [(date(2025, 4, 1), 2.1)]
    assert seen == [("/api/table/tabledata/M182342", USER_AGENT)]


def test_a_missing_row_an_empty_row_or_a_bad_table_id_is_an_error():
    ok = httpx.Response(200, json=table([row("1", ("2025 1Q", ""))]))
    with pytest.raises(SingStatError, match="no series 9"):
        client_for(lambda r: ok).series("M182342", "9")
    with pytest.raises(SingStatError, match="no observations"):
        client_for(lambda r: ok).series("M182342", "1")
    with pytest.raises(SingStatError):
        client_for(lambda r: ok).series("../x", "1")


def test_after_a_refusal_the_client_stops_asking_for_the_run():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = client_for(handler)
    with pytest.raises(SingStatError):
        client.series("M182342", "1")
    first = len(calls)
    with pytest.raises(SingStatError, match="not asking again"):
        client.series("M182342", "1")
    assert len(calls) == first


def test_a_quarter_is_dated_the_last_weekday_of_the_month_after_it_ends():
    assert singapore_quarterly_release(date(2026, 7, 1)) == date(2026, 10, 30)


def test_the_catalog_declares_the_series_from_1990():
    spec = SINGSTAT_BY_ID["SINGSTAT_UNE"]
    entry = BY_ID[spec.id]
    assert entry.source == "singstat" and entry.country == "SG"
    assert entry.history_start == HISTORY_START and spec.concept == "unemployment_rate"
    assert spec.table == "M182342" and spec.series_no == "1"


def test_ingest_stores_quarters_dated_by_the_rule(db_session):
    results = ingest_national.ingest_singstat(
        client_for(
            lambda r: httpx.Response(
                200, json=table([row("1", ("2026 2Q", "2.0"), ("2026 3Q", "1.9"))])
            )
        ),
        db_session,
        ["SINGSTAT_UNE", "NOT_SS"],
        today=date(2026, 11, 13),
        sleep=lambda _s: None,
    )
    by_id = {r.series_id: r for r in results}
    assert by_id["SINGSTAT_UNE"].rows == 2
    assert by_id["NOT_SS"].error == "not a SingStat series in the catalog"
    store = MacroStore(db_session)
    seen = {v.period: v.realtime_start for v in store.as_of("SINGSTAT_UNE", date(2026, 11, 13))}
    assert seen[date(2026, 7, 1)] == date(2026, 10, 30)
    assert store.get_series("SINGSTAT_UNE").frequency == "Quarterly"
