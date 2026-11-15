"""Rule 23: every series records its unit kind and currency; only a common basis compares."""

import re
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.data.macro_catalog import CATALOG
from app.data.series_units import SERIES_UNITS
from app.domain.units import UNIT_KINDS, classify, comparable
from app.jobs.check_data import unit_review_reason
from app.stores.macro import SeriesMeta
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

MONEY = {"amount_currency", "price_per_unit"}


def test_every_catalog_series_declares_a_known_unit_kind_and_currency():
    assert {e.id for e in CATALOG} == set(SERIES_UNITS), "declare every series, and only those"
    for series_id, (kind, currency) in SERIES_UNITS.items():
        assert kind in UNIT_KINDS and kind != "unknown", f"{series_id}: a person must decide"
        if kind in MONEY:
            assert currency and re.fullmatch(r"[A-Z]{3}", currency), series_id
        else:
            assert currency is None, f"{series_id}: {kind} has no currency"


@pytest.mark.parametrize(
    ("units", "country", "kind", "currency"),
    [
        ("Billions of Chained 2017 Dollars", "US", "amount_currency", "USD"),  # FRED
        ("Millions of Euro", "EA", "amount_currency", "EUR"),  # ECB UNIT_MULT + UNIT
        ("Dollars per Barrel", "US", "price_per_unit", "USD"),
        ("Japanese Yen to One U.S. Dollar", "US", "price_per_unit", "JPY"),
        ("U.S. Dollars to One Euro", "US", "price_per_unit", "USD"),
        ("Index, long-term average = 100", "JP", "index", None),  # OECD
        ("Percent per annum", "EA", "rate_percent", None),
        ("Percent of GDP", "US", "ratio", None),
        ("Thousands of Persons", "US", "count", None),
        ("Thousand Barrels per Day", "US", "other", None),  # EIA
        ("Billions of Chained 2015 Yen", "JP", "amount_currency", "JPY"),  # FRED
        (
            "Millions of Domestic Currency",
            "CA",
            "amount_currency",
            "CAD",
        ),  # FRED: the country's own
        ("Millions of Pounds, chained volume measures", "GB", "amount_currency", "GBP"),  # ONS
        ("Dollars per Pound", "US", "price_per_unit", "USD"),  # a weight, not sterling
        ("Millions of Domestic Currency", "ZZ", "unknown", None),  # no such country: not guessed
        ("Dollars", "CA", "unknown", None),  # which dollar is not stated: never guessed
        ("Kilotonnes of oil equivalent", "US", "unknown", None),
    ],
)
def test_classify_reads_the_sources_own_units(units, country, kind, currency):
    unit = classify(units, country)
    assert (unit.kind, unit.currency) == (kind, currency)


def _same(a, b, a_country="US", b_country="US"):
    return comparable(classify(a, a_country), classify(b, b_country)).same_scale


def test_comparable_needs_the_same_kind_currency_and_unit():
    assert _same("Millions of Dollars", "Billions of Dollars")  # rescaled, same unit
    assert _same("Percent", "Percent per annum", b_country="EA")  # US and euro area policy rates
    assert _same("Index 2017=100", "Index 2017=100")
    assert _same("Index, long-term average = 100", "Index, long-term average = 100", "JP", "GB")
    assert _same("Dollars per Barrel", "Dollars per Barrel")  # WTI and Brent
    assert not _same("Billions of Dollars", "Millions of Euro", b_country="EA")  # convert first
    assert not _same("Billions of Dollars", "Billions of Chained 2017 Dollars")  # nominal vs real
    assert not _same("Dollars per Barrel", "Dollars per Gallon")
    assert not _same("Index 2017=100", "Index 1982-1984=100")  # rebase first
    assert not _same("Index", "Index")  # diffusion or standardised readings: no stated base
    assert not _same("Number", "Level in Thousands")  # counts of unstated things
    assert not _same("Thousands of Persons", "Percent")  # a count beside a rate
    assert not _same("Dollars", "Dollars", "CA", "CA")  # unknown never compares
    reason = comparable(classify("Billions of Dollars", "US"), classify("Millions of Euro", "EA"))
    assert "convert at a stated rate" in reason.reason


def _meta(series_id, units):
    return SeriesMeta(
        series_id,
        "fred",
        "t",
        units,
        "Monthly",
        "SA",
        "US",
        "labour",
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_release_check_flags_a_unit_that_no_longer_matches_the_declaration():
    assert unit_review_reason(_meta("UNRATE", "Percent")) is None
    reason = unit_review_reason(_meta("UNRATE", "Thousands of Persons"))
    assert "declared rate_percent" in reason
    assert "No declared unit" in unit_review_reason(_meta("NOT_IN_CATALOG", "Percent"))


def test_store_derives_and_api_returns_unit_kind_and_currency(client, ingested):  # noqa: F811
    [series] = client.get("/v1/macro/series").json()
    assert (series["unitKind"], series["currency"]) == ("rate_percent", None)
    assert replace(_meta("UNRATE", "Percent")).unit_kind is None  # ingest jobs never set it
