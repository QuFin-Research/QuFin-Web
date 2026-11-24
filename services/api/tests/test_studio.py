"""The comparison studio API: 10-country cap, common frequency, SA/NSA, PoC, overlay.

Rules 30 to 32 and 22.
"""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date, timedelta

import pytest

from app.core.clock import today as today_dependency
from app.data.macro_catalog import BY_ID
from app.stores.macro import MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

TODAY = date(2026, 11, 12)
OPEN = date(9999, 12, 31)


def put(session, series_id, country, units, frequency, adjustment, periods, values):
    entry = BY_ID[series_id]
    MacroStore(session).replace_series(
        SeriesMeta(
            id=series_id,
            source=entry.source,
            title=f"{series_id} (test)",
            units=units,
            frequency=frequency,
            seasonal_adjustment=adjustment,
            country=country,
            dimension=entry.dimension,
            last_updated=None,
            cycle=entry.cycle,
            source_name="Test publisher",
        ),
        [Vintage(p, p + timedelta(days=20), OPEN, v) for p, v in zip(periods, values, strict=True)],
    )


def month_starts(count, last=date(2026, 9, 1)):
    end = last.year * 12 + last.month - 1
    return [date((end - i) // 12, (end - i) % 12 + 1, 1) for i in reversed(range(count))]


def saturdays(count, last=date(2026, 11, 7)):
    return [last - timedelta(days=7 * i) for i in reversed(range(count))]


@pytest.fixture
def studio(app, db_session):
    app.dependency_overrides[today_dependency] = lambda: TODAY
    months = month_starts(24)
    put(
        db_session,
        "UNRATE",
        "US",
        "Percent",
        "Monthly",
        "Seasonally Adjusted",
        months,
        [4.0 + 0.1 * (i % 4) for i in range(24)],
    )
    put(
        db_session,
        "OECD_UNE_DEU",
        "DE",
        "Percent",
        "Monthly",
        "Seasonally Adjusted",
        months,
        [3.0] * 24,
    )
    put(
        db_session,
        "ICSA",
        "US",
        "Number",
        "Weekly, Ending Saturday",
        "Seasonally Adjusted",
        saturdays(60),
        [200000.0 + i for i in range(60)],
    )
    yield
    app.dependency_overrides.pop(today_dependency, None)


def get(client, **params):
    return client.get("/v1/studio/compare", params=params)


def test_more_than_ten_countries_is_refused_in_the_api(studio, client):
    codes = ["USA", "DEU", "FRA", "GBR", "JPN", "CAN", "AUS", "ITA", "KOR", "MEX", "TUR"]
    res = get(client, concept="unemployment_rate", countries=codes)
    assert res.status_code == 422 and "1 to 10" in res.json()["detail"]
    assert get(client, concept="unemployment_rate", countries=codes[:10]).status_code == 200


def test_countries_share_one_frequency_and_say_which_are_available(studio, client):
    body = get(client, concept="unemployment_rate", countries="USA,DEU").json()
    assert body["frequency"] == "monthly"
    assert body["allowedFrequencies"] == ["monthly", "quarterly", "semi_annual", "annual"]
    assert "Monthly, Quarterly, Semi-Annual and Annual" in body["restriction"]
    assert {s["iso3"] for s in body["series"]} == {"USA", "DEU"}
    assert all(s["adjustment"] == "SA" and s["lastVintage"] for s in body["series"])
    assert body["notices"] == []


def test_a_faster_frequency_than_the_slowest_series_is_refused(studio, client):
    res = get(client, concept="unemployment_rate", countries="USA,DEU", frequency="weekly")
    assert res.status_code == 422 and "constrained by" in res.json()["detail"]


def test_quarterly_means_the_average_of_each_complete_quarter(studio, client):
    body = get(client, concept="unemployment_rate", countries="DEU", frequency="quarterly").json()
    deu = body["series"][0]
    assert deu["aggregation"] == "mean" and len(deu["points"]) == 8
    assert all(p["value"] == pytest.approx(3.0) for p in deu["points"])


def test_poc_of_a_rate_is_a_difference_in_points(studio, client):
    body = get(client, concept="unemployment_rate", countries="USA", metric="poc").json()
    usa = body["series"][0]
    assert usa["displayUnit"] == "pp" and body["pocName"] == "Month-over-Month"
    assert usa["points"][0]["value"] == pytest.approx(0.1)  # 4.0 -> 4.1
    assert "never changed in percent" in usa["metricNote"]


def test_mixed_adjustments_are_disclosed(studio, client, db_session):
    put(
        db_session,
        "OECD_UNE_DEU",
        "DE",
        "Percent",
        "Monthly",
        "Not Seasonally Adjusted",
        month_starts(24),
        [3.0] * 24,
    )
    body = get(client, concept="unemployment_rate", countries="USA,DEU").json()
    assert {s["adjustment"] for s in body["series"]} == {"SA", "NSA"}
    assert any("mix adjustments" in n for n in body["notices"])


def test_a_country_without_a_series_is_named_not_invented(studio, client):
    body = get(client, concept="unemployment_rate", countries="USA,FRA").json()
    assert [s["iso3"] for s in body["series"]] == ["USA"]
    assert any("France" in n for n in body["notices"])


def test_unknown_inputs_are_refused(studio, client):
    assert get(client, concept="nope_not_a_concept", countries="USA").status_code == 404
    assert get(client, concept="unemployment_rate", countries="ZZZ").status_code == 404
    assert get(client, concept="unemployment_rate", countries=[]).status_code == 422


def test_usd_conversion_preserves_native_value_and_normalizes_source_scale(
    studio, client, db_session
):
    month = month_starts(24)
    put(
        db_session,
        "BOPGSTB",
        "US",
        "Millions of Dollars",
        "Monthly",
        "Not Seasonally Adjusted",
        month,
        [100.0] * len(month),
    )
    body = get(client, concept="trade_balance", countries="USA", convertTo="USD").json()
    series = body["series"][0]
    assert series["nativeCurrency"] == "USD"
    assert series["displayCurrency"] == "USD"
    assert series["displayUnit"] == "USD"
    assert series["points"][0]["nativeValue"] == 100.0
    assert series["points"][0]["value"] == 100_000_000.0


def test_foreign_currency_flow_is_aggregated_before_fx_conversion(studio, client, db_session):
    months = month_starts(24)
    put(
        db_session,
        "BOPGSTB",
        "US",
        "Millions of Euros",
        "Monthly",
        "Not Seasonally Adjusted",
        months,
        [100.0] * len(months),
    )
    fx_periods = [date(month.year, month.month, 15) for month in months]
    put(
        db_session,
        "DEXUSEU",
        "US",
        "U.S. Dollars to One Euro",
        "Daily",
        "Not Seasonally Adjusted",
        fx_periods,
        [1.0 + 0.2 * (index % 3) for index in range(len(fx_periods))],
    )

    body = get(
        client, concept="trade_balance", countries="USA", frequency="quarterly", convertTo="USD"
    ).json()
    series = body["series"][0]
    point = series["points"][0]
    assert series["aggregation"] == "sum"
    assert point["nativeValue"] == 300.0
    assert point["fxRate"] == pytest.approx(1.2)
    assert point["value"] == pytest.approx(360_000_000.0)


def test_usd_conversion_refuses_non_monetary_series(studio, client):
    response = get(client, concept="unemployment_rate", countries="USA", convertTo="USD")
    assert response.status_code == 422
    assert "amount in a known currency" in response.json()["detail"]


def test_overlay_puts_weekly_claims_down_to_monthly_sums_on_their_own_axis(studio, client):
    res = client.get(
        "/v1/studio/overlay",
        params={"country": "USA", "seriesIds": ["UNRATE", "ICSA"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "indicators" and body["frequency"] == "monthly"
    by_id = {s["seriesId"]: s for s in body["series"]}
    assert by_id["ICSA"]["aggregation"] == "sum" and by_id["UNRATE"]["aggregation"] is None
    assert by_id["ICSA"]["axis"] != by_id["UNRATE"]["axis"]
    assert by_id["ICSA"]["points"][0]["value"] > 400000  # a month of weekly claims, summed
    assert "constrained by" in body["restriction"]


def test_overlay_refuses_a_series_the_country_does_not_have(studio, client):
    res = client.get("/v1/studio/overlay", params={"country": "DEU", "seriesIds": ["UNRATE"]})
    assert res.status_code == 404


def test_catalog_lists_indicators_adjustment_tags_and_the_cap(studio, client):
    body = client.get("/v1/studio/catalog").json()
    assert body["maxCountries"] == 10 and "weekly" in body["frequencies"]
    concept = next(i for i in body["indicators"] if i["concept"] == "unemployment_rate")
    assert {"USA", "DEU"} <= set(concept["countries"])
    icsa = next(s for s in body["series"] if s["seriesId"] == "ICSA")
    assert icsa["nativeFrequency"] == "weekly" and icsa["adjustment"] == "SA"
