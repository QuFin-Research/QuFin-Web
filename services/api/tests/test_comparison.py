"""Countries compared on one basis: CPI as year-on-year change, unemployment as a rate."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date, timedelta

import pytest

from app.core.clock import today as today_dependency
from app.data.macro_catalog import BY_ID
from app.data.macro_ids import IMF_CPI, OECD_MACRO
from app.domain.comparison import BASES, Point, on_basis, points_ago, year_on_year
from app.stores.macro import MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

TODAY = date(2026, 11, 12)
OPEN = date(9999, 12, 31)


def months(first: date, count: int) -> list[date]:
    return [
        date(first.year + (first.month - 1 + i) // 12, (first.month - 1 + i) % 12 + 1, 1)
        for i in range(count)
    ]


# --- the arithmetic ---------------------------------------------------------------------------


def test_an_index_level_becomes_its_year_on_year_change():
    index = [Point(p, 100.0 * 1.03 ** (i / 12)) for i, p in enumerate(months(date(2024, 1, 1), 26))]
    yoy = year_on_year(index)
    assert len(yoy) == 14  # the first twelve months have no year-ago month
    assert yoy[0].period == date(2025, 1, 1)
    assert all(abs(p.value - 3.0) < 1e-6 for p in yoy)


def test_a_series_published_as_a_change_is_never_changed_again():
    published = [Point(p, 3.1) for p in months(date(2025, 1, 1), 14)]
    assert on_basis("consumer_prices", published, published_as_change=True) == published


def test_a_missing_month_drops_that_period_instead_of_guessing():
    index = [Point(p, 100.0) for p in months(date(2024, 1, 1), 26)]
    del index[14]  # March 2025 is missing
    periods = {p.period for p in year_on_year(index)}
    assert date(2025, 3, 1) not in periods and date(2025, 4, 1) in periods


def test_zero_base_is_skipped_and_unemployment_is_left_as_a_rate():
    assert year_on_year([Point(date(2024, 1, 1), 0.0), Point(date(2025, 1, 1), 5.0)]) == []
    rate = [Point(date(2026, 8, 1), 4.2), Point(date(2026, 7, 1), 4.1)]
    assert [p.value for p in on_basis("unemployment_rate", rate)] == [4.1, 4.2]


def test_points_ago_needs_that_exact_month():
    series = [Point(p, float(i)) for i, p in enumerate(months(date(2026, 1, 1), 9))]
    assert points_ago(series, 3) == Point(date(2026, 6, 1), 5.0)
    assert points_ago(series, 12) is None
    assert points_ago([], 3) is None


def test_the_catalog_series_of_a_comparison_are_on_the_basis_it_names():
    for series_id in IMF_CPI:
        assert BY_ID[series_id].published_as_change and BY_ID[series_id].change == "diff"
    for series_id in OECD_MACRO:
        assert BY_ID[series_id].change == "diff"
    assert set(BASES) == {"consumer_prices", "unemployment_rate"}


# --- the endpoint -----------------------------------------------------------------------------


def seed(session, series_id, country, units, values, adjustment="Not Seasonally Adjusted"):
    """Monthly values ending September 2026, each first published 45 days after its month."""
    periods = months(date(2026, 9, 1) - timedelta(days=0), 1)
    first = date(2026, 9, 1)
    start_index = first.year * 12 + first.month - len(values)
    periods = [
        date((start_index + i) // 12, (start_index + i) % 12 + 1, 1) for i in range(len(values))
    ]
    entry = BY_ID[series_id]
    MacroStore(session).replace_series(
        SeriesMeta(
            id=series_id,
            source=entry.source,
            title=f"{series_id} (test)",
            units=units,
            frequency="Monthly",
            seasonal_adjustment=adjustment,
            country=country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name="Test publisher (from national sources)",
        ),
        [Vintage(p, p + timedelta(days=45), OPEN, v) for p, v in zip(periods, values, strict=True)],
    )


@pytest.fixture
def compared(app, db_session):
    app.dependency_overrides[today_dependency] = lambda: TODAY
    # US: an index level rising 3% a year; Germany and Japan: published annual rates.
    seed(
        db_session,
        "CPIAUCSL",
        "US",
        "Index 1982-1984=100",
        [300 * 1.03 ** (i / 12) for i in range(26)],
    )
    seed(db_session, "IMF_CPI_DEU", "DE", "Percentage change", [2.0 + 0.1 * i for i in range(26)])
    seed(db_session, "IMF_CPI_JPN", "JP", "Percentage change", [1.0] * 26)
    seed(
        db_session,
        "UNRATE",
        "US",
        "Percent",
        [4.0 + 0.1 * (i % 3) for i in range(26)],
        "Seasonally Adjusted",
    )
    seed(db_session, "OECD_UNE_DEU", "DE", "Percent", [3.8] * 26, "Seasonally Adjusted")
    yield
    app.dependency_overrides.pop(today_dependency, None)


def test_prices_are_compared_as_year_on_year_change_whatever_each_country_stores(compared, client):
    res = client.get("/v1/macro/compare/consumer_prices")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["data"] == "live" and body["basis"] == "Year-on-year change" and body["unit"] == "%"
    rows = {r["iso3"]: r for r in body["rows"]}
    assert set(rows) == {"USA", "DEU", "JPN"}
    assert rows["USA"]["value"] == 3.0 and rows["USA"]["converted"] is True
    assert rows["USA"]["storedAs"] == "Index 1982-1984=100"  # never shown as if it were a rate
    assert rows["DEU"]["converted"] is False and rows["DEU"]["value"] == pytest.approx(4.5)
    assert [r["iso3"] for r in body["rows"]] == ["DEU", "USA", "JPN"]  # highest first
    assert "converted" in body["method"] and "published" in body["method"]


def test_changes_are_in_points_and_history_is_on_the_same_basis(compared, client):
    rows = {r["iso3"]: r for r in client.get("/v1/macro/compare/consumer_prices").json()["rows"]}
    deu = rows["DEU"]
    assert deu["change3M"] == pytest.approx(0.3) and deu["change12M"] == pytest.approx(1.2)
    assert len(deu["history"]) == 26 and deu["history"][-1]["value"] == deu["value"]
    assert rows["JPN"]["change12M"] == 0.0
    assert (
        len(rows["USA"]["history"]) == 14
    )  # the US needs a year of index levels before its first change


def test_unemployment_is_a_rate_and_unlisted_countries_are_reported_missing(compared, client):
    body = client.get("/v1/macro/compare/unemployment_rate").json()
    assert body["unit"] == "%" and "converted" not in body["method"]
    assert {r["iso3"]: r["converted"] for r in body["rows"]} == {"USA": False, "DEU": False}
    missing = {m["iso3"]: m["name"] for m in body["missing"]}
    assert missing["FRA"] == "France" and "DEU" not in missing


def test_an_overdue_series_is_shown_but_ranked_last_and_marked_unusable(compared, app, client):
    app.dependency_overrides[today_dependency] = lambda: TODAY + timedelta(days=400)
    rows = client.get("/v1/macro/compare/unemployment_rate").json()["rows"]
    assert [r["usable"] for r in rows] == [False, False]
    assert all("due" in r["statusNote"] for r in rows)


def test_an_indicator_without_a_comparison_basis_is_refused(client):
    res = client.get("/v1/macro/compare/policy_rate")
    assert res.status_code == 404 and "consumer_prices" in res.json()["detail"]
    assert client.get("/v1/macro/compare/Not-A-Concept").status_code == 422
