"""Treasury Fiscal Data: release dates, connector and ingest."""

from datetime import date

import httpx
import pytest

from app.connectors.treasury import TreasuryClient, TreasuryError
from app.data.treasury_calendar import debt_to_penny_release, monthly_release
from app.jobs import ingest_treasury
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)


@pytest.mark.parametrize(
    ("record", "released"),
    [
        (date(2026, 11, 4), date(2026, 11, 5)),  # Wednesday -> Thursday
        (date(2026, 11, 6), date(2026, 11, 9)),  # Friday -> Monday
        (date(2026, 11, 10), date(2026, 11, 12)),  # Veterans Day skipped (as on the calendar)
    ],
)
def test_debt_to_penny_is_published_the_next_business_day(record, released):
    assert debt_to_penny_release(record) == released


@pytest.mark.parametrize(
    ("month", "released"),
    [
        (date(2026, 10, 1), date(2026, 11, 5)),  # Fiscal Data calendar, checked 5 Nov 2026
        (date(2026, 11, 1), date(2026, 12, 4)),
        (date(2026, 12, 1), date(2027, 1, 7)),  # New Year's Day is not a business day
    ],
)
def test_monthly_datasets_are_published_on_the_fourth_business_day(month, released):
    assert monthly_release(month) == released


def _client(routes):
    def handler(request: httpx.Request):
        path = request.url.path.rsplit("/", 1)[-1]
        rows = routes[path]
        size = int(request.url.params["page[size]"])
        page = int(request.url.params["page[number]"])
        pages = max(1, -(-len(rows) // size))
        assert request.url.params["filter"].startswith("record_date:gte:")
        return httpx.Response(
            200,
            json={"data": rows[(page - 1) * size : page * size], "meta": {"total-pages": pages}},
        )

    return TreasuryClient(transport=httpx.MockTransport(handler), sleep=lambda _s: None)


EXPENSE = [
    {"record_date": "2026-09-30", "month_expense_amt": "60.5"},
    {"record_date": "2026-09-30", "month_expense_amt": "-0.5"},  # amortised premium
    {"record_date": "2026-10-31", "month_expense_amt": "100"},
    {"record_date": "2026-10-31", "month_expense_amt": "4.4"},
]


def test_interest_expense_sums_every_line_per_month(monkeypatch):
    from app.connectors import treasury

    monkeypatch.setattr(treasury, "PAGE_SIZE", 3)  # forces a second page
    client = _client({"interest_expense": EXPENSE})
    assert client.interest_expense(date(2026, 1, 1)) == [
        (date(2026, 9, 1), 60.0),
        (date(2026, 10, 1), 104.4),
    ]


def test_missing_rate_class_fails_instead_of_loading_nothing():
    client = _client({"avg_interest_rates": []})
    with pytest.raises(TreasuryError):
        client.average_interest_rate("Total Marketable", date(2026, 1, 1))
    with pytest.raises(TreasuryError):
        client.average_interest_rate("Total,record_date:lt:2000", date(2026, 1, 1))


def test_ingest_dates_records_by_their_release(db_session):  # noqa: F811
    client = _client(
        {
            "debt_to_penny": [
                {"record_date": "2026-11-03", "tot_pub_debt_out_amt": "40547403570984.82"},
                {"record_date": "2026-11-04", "tot_pub_debt_out_amt": "40550000000000.00"},
            ],
            "avg_interest_rates": [{"record_date": "2026-10-31", "avg_interest_rate_amt": "3.570"}],
            "interest_expense": EXPENSE,
        }
    )
    results = ingest_treasury.ingest(
        client, db_session, [*ingest_treasury.SERIES, "UNRATE"], today=date(2026, 11, 6)
    )
    assert [r.rows for r in results[:3]] == [2, 1, 2]
    assert results[3].error == "not a Treasury series in the catalog"
    store = MacroStore(db_session)
    # The 4 November figure was public on 5 November, not before.
    assert [v.value for v in store.as_of("TREAS_DEBT_TOTAL", date(2026, 11, 4))] == [
        40547403570984.82
    ]
    assert store.as_of("TREAS_AVG_RATE_MARKETABLE", date(2026, 11, 4)) == []
    assert store.get_series("TREAS_INTEREST_EXPENSE").source_name.startswith("U.S. Department")
