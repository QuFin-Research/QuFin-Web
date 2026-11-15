"""One publisher spelling, and concepts whose countries do not share a scale (rule 23)."""

# Publisher names are long, exact strings: wrapping them would hide what is being compared.
# ruff: noqa: E501

import pytest

from app.data.indicator_concepts import COMPARED_AS, SERIES_CONCEPTS
from app.data.macro_catalog import CATALOG
from app.data.publishers import ALIASES, canonical_publisher
from app.domain.comparability import concept_scales
from app.domain.units import classify
from app.jobs.check_data import comparability_reasons
from app.stores.macro import MacroSeriesRow, MacroStore, SeriesMeta
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

# --- publishers ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stated", "canonical"),
    [
        ("International Monetary Fund (from national central banks)", "International Monetary Fund"),
        ("International Monetary Fund", "International Monetary Fund"),
        ("OECD (from national sources)", "OECD"),
        ("OECD", "OECD"),
        ("Bank for International Settlements (from national central banks)", "Bank for International Settlements"),
        ("U.S. Department of the Treasury. Fiscal Service", "U.S. Department of the Treasury, Bureau of the Fiscal Service"),
        ("U.S. Department of the Treasury, Bureau of the Fiscal Service", "U.S. Department of the Treasury, Bureau of the Fiscal Service"),
        ("Board of Governors of the Federal Reserve System (US)", "Board of Governors of the Federal Reserve System"),
        ("Board of Governors of the Federal Reserve System (H.15); spread calculated by FRED", "Board of Governors of the Federal Reserve System"),
        ("U.S. Census Bureau; U.S. Bureau of Economic Analysis", "U.S. Census Bureau; U.S. Bureau of Economic Analysis"),
        ("  U.S.   Bureau of Labor Statistics ", "U.S. Bureau of Labor Statistics"),
    ],
)  # fmt: skip
def test_the_same_organisation_has_one_spelling(stated, canonical):
    assert canonical_publisher(stated) == canonical


def test_unknown_names_pass_through_and_nothing_stays_nothing():
    assert canonical_publisher("Some New Agency") == "Some New Agency"
    assert canonical_publisher("Some Agency (from its members)") == "Some Agency"
    assert canonical_publisher(None) is None
    assert canonical_publisher("   ") is None


def test_every_alias_maps_to_a_name_that_is_itself_canonical():
    for canonical in ALIASES.values():
        assert canonical_publisher(canonical) == canonical


def test_ingest_stores_the_canonical_publisher_next_to_the_sources_wording(db_session, ingested):  # noqa: F811
    row = db_session.get(MacroSeriesRow, "UNRATE")
    assert row.source_name == "U.S. Bureau of Labor Statistics"
    assert row.publisher == "U.S. Bureau of Labor Statistics"


def test_a_publisher_qualifier_is_kept_in_source_name_but_not_in_publisher(db_session, ingested):  # noqa: F811
    store = MacroStore(db_session)
    meta = store.get_series("UNRATE")
    store.replace_series(
        SeriesMeta(**{**meta.__dict__, "source_name": "OECD (from national sources)"}), []
    )
    row = db_session.get(MacroSeriesRow, "UNRATE")
    assert (row.source_name, row.publisher) == ("OECD (from national sources)", "OECD")


# --- scales ----------------------------------------------------------------------------------


def unit(units, country="US", source="fred"):
    return classify(units, country, source)


def test_series_on_one_scale_are_comparable_and_unlike_ones_say_why():
    same = concept_scales({"unemployment_rate": [unit("Percent"), unit("Percent", "GB", "oecd")]})
    assert same["unemployment_rate"].same_scale
    mixed = concept_scales(
        {"consumer_prices": [unit("Index 1982-1984=100"), unit("Percentage change", "EA", "ecb")]}
    )
    assert not mixed["consumer_prices"].same_scale
    assert "index" in mixed["consumer_prices"].reason
    assert "rate_percent" in mixed["consumer_prices"].reason


def test_an_unlabelled_index_and_a_different_currency_are_not_the_same_scale():
    assert not concept_scales({"x": [unit("Index"), unit("Index, long-term average = 100")]})[
        "x"
    ].same_scale
    assert not concept_scales(
        {"y": [unit("Billions of Dollars"), unit("Millions of Euro", "EA", "ecb")]}
    )["y"].same_scale


def metas_for(*pairs):
    return {
        series_id: SeriesMeta(
            id=series_id,
            source=source,
            title="t",
            units=units,
            frequency="Monthly",
            seasonal_adjustment="Not Seasonally Adjusted",
            country=country,
            dimension="inflation",
            last_updated=None,
        )
        for series_id, country, source, units in pairs
    }


def test_a_concept_with_mixed_scales_that_is_not_declared_fails_the_check():
    # UNRATE and a pretend second country's unemployment rate in index points
    SERIES_CONCEPTS[("GB", "FAKE_UNRATE")] = "unemployment_rate"
    try:
        reasons = comparability_reasons(
            metas_for(
                ("UNRATE", "US", "fred", "Percent"),
                ("FAKE_UNRATE", "GB", "fred", "Index, 2015=100"),
            )
        )
    finally:
        del SERIES_CONCEPTS[("GB", "FAKE_UNRATE")]
    assert set(reasons) == {"UNRATE", "FAKE_UNRATE"}
    assert "COMPARED_AS" in reasons["UNRATE"] and "rule 23" in reasons["UNRATE"]


def test_a_declared_concept_does_not_fail_and_one_scale_never_does():
    declared = metas_for(
        ("CPIAUCSL", "US", "fred", "Index 1982-1984=100"),
        ("HICP.M.U2.N.000000.4D0.ANR", "EA", "ecb", "Percentage change"),
    )
    assert comparability_reasons(declared) == {}
    assert comparability_reasons(metas_for(("UNRATE", "US", "fred", "Percent"))) == {}


def test_every_declared_basis_refers_to_a_shared_concept_and_says_how_countries_compare():
    from collections import defaultdict

    # The units text comes from the sources, so the real check runs on stored series (check-data);
    # here the declarations themselves must refer to real, shared concepts and say how.
    concepts = defaultdict(int)
    for s in CATALOG:
        concepts[SERIES_CONCEPTS[(s.country, s.id)]] += 1
    for concept, basis in COMPARED_AS.items():
        assert concepts[concept] > 1, f"{concept} is declared but has one country or none"
        assert len(basis) > 30  # says how countries are compared, not just a label


def test_the_indicators_endpoint_says_when_countries_share_a_scale(ingested, client):  # noqa: F811
    [indicator] = client.get("/v1/macro/indicators").json()
    assert indicator["sameScale"] is True
    assert indicator["scaleNote"] is None and indicator["comparedAs"] is None
