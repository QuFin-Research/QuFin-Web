from datetime import date

import pytest

from app.data.macro_catalog import BY_ID
from app.domain.currency import FX_SERIES, CurrencyService
from app.domain.harmonize import Obs, aggregate
from app.stores.macro import Vintage

OPEN = date(9999, 12, 31)


class Store:
    def __init__(self, vintages):
        self.vintages = vintages
        self.requested = []

    def as_of(self, series_id, as_of=None):
        self.requested.append((series_id, as_of))
        return self.vintages.get(series_id, [])


def vintage(period, value, released=None):
    return Vintage(period, released or period, OPEN, value)


def test_fx_registry_only_references_catalog_series():
    assert FX_SERIES
    assert all(series_id in BY_ID for series_id, _ in FX_SERIES.values())


def test_usd_is_an_identity_conversion_without_an_fx_read():
    store = Store({})
    result = CurrencyService(store).convert_points(
        [(date(2026, 1, 1), 12.5)], "USD", "Monthly", is_flow=True
    )[0]
    assert result.value_usd == 12.5
    assert result.usable and result.method == "identity"
    assert store.requested == []


def test_flow_uses_the_average_usd_rate_inside_the_aligned_period():
    store = Store(
        {
            "DEXUSEU": [
                vintage(date(2026, 1, 9), 1.1),
                vintage(date(2026, 2, 6), 1.3),
                vintage(date(2026, 4, 3), 9.0),
            ]
        }
    )
    result = CurrencyService(store).convert_points(
        [(date(2026, 1, 1), 100.0)],
        "EUR",
        "Quarterly",
        is_flow=True,
        as_of=date(2026, 3, 31),
    )[0]
    assert result.value_usd == pytest.approx(120.0)
    assert result.fx_rate == pytest.approx(1.2)
    assert result.fx_rate_date == date(2026, 2, 6)
    assert result.fx_source == "DEXUSEU"
    assert store.requested == [("DEXUSEU", date(2026, 3, 31))]


def test_flow_is_summed_before_period_average_fx_conversion():
    monthly = [
        Obs(date(2026, 1, 1), 10.0),
        Obs(date(2026, 2, 1), 20.0),
        Obs(date(2026, 3, 1), 30.0),
    ]
    quarterly = aggregate(monthly, "monthly", "quarterly", "sum")
    store = Store(
        {
            "DEXUSEU": [
                vintage(date(2026, 1, 9), 1.1),
                vintage(date(2026, 2, 6), 1.3),
                vintage(date(2026, 3, 6), 1.5),
            ]
        }
    )
    result = CurrencyService(store).convert_points(
        [(point.period, point.value) for point in quarterly],
        "EUR",
        "Quarterly",
        is_flow=True,
    )[0]
    assert result.native_value == 60.0
    assert result.value_usd == pytest.approx(78.0)


def test_inverse_quotes_are_inverted_before_averaging():
    store = Store(
        {
            "DEXJPUS": [
                vintage(date(2026, 1, 9), 100.0),
                vintage(date(2026, 2, 6), 200.0),
            ]
        }
    )
    result = CurrencyService(store).convert_points(
        [(date(2026, 1, 1), 2.0)], "JPY", "Quarterly", is_flow=True
    )[0]
    assert result.fx_rate == pytest.approx(0.0075)
    assert result.value_usd == pytest.approx(0.015)


def test_stock_uses_the_last_rate_on_or_before_the_period_end():
    store = Store(
        {
            "DEXUSEU": [
                vintage(date(2025, 12, 31), 1.0),
                vintage(date(2026, 1, 16), 1.2),
                vintage(date(2026, 2, 1), 1.5),
            ]
        }
    )
    result = CurrencyService(store).convert_points(
        [(date(2026, 1, 1), 10.0)], "EUR", "Monthly", is_flow=False
    )[0]
    assert result.fx_rate == 1.2
    assert result.fx_rate_date == date(2026, 1, 16)
    assert result.value_usd == 12.0


def test_unconvertible_currency_is_logged_and_returns_unusable_points(caplog):
    result = CurrencyService(Store({})).convert_points(
        [(date(2026, 1, 1), 10.0)], "BRL", "Monthly", is_flow=True
    )[0]
    assert not result.usable and result.value_usd is None
    assert result.reason and "Rule 37" in result.reason
    assert "Rule 37" in caplog.text
