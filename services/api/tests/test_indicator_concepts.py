"""The indicator catalog rules (services/api/CLAUDE.md, rules 16-18). Do not loosen these."""

from collections import Counter

from app.data.indicator_concepts import (
    ACRONYMS,
    CONCEPTS,
    LOCAL_ALIASES,
    NON_FRED_ALLOWED,
    REDUNDANT,
    SERIES_CONCEPTS,
    concept_for,
)
from app.data.macro_catalog import CATALOG
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)


def test_every_series_has_a_display_name_and_plain_explanation():
    for entry in CATALOG:
        concept = concept_for(entry.country, entry.id)
        assert concept is not None, f"{entry.id} has no display name"
        assert concept.name and len(concept.name) <= 64, entry.id
        assert concept.explanation.endswith("."), entry.id
        assert len(concept.explanation) <= 120, f"{entry.id}: keep it to one plain sentence"


def test_no_duplicated_indicators_within_a_country():
    pairs = Counter((e.country, SERIES_CONCEPTS[(e.country, e.id)]) for e in CATALOG)
    duplicates = [key for key, n in pairs.items() if n > 1]
    assert not duplicates, f"two series measure the same thing: {duplicates}"
    assert len({e.id for e in CATALOG}) == len(CATALOG), "a series is listed twice"


def test_display_names_are_unique_so_users_never_see_two_identical_labels():
    names = Counter(c.name for c in CONCEPTS.values())
    assert [n for n, k in names.items() if k > 1] == []


def test_every_concept_is_used_and_every_mapping_is_in_the_catalog():
    catalog = {(e.country, e.id) for e in CATALOG}
    assert set(SERIES_CONCEPTS) == catalog
    assert set(SERIES_CONCEPTS.values()) == set(CONCEPTS)


def test_series_derivable_from_stored_ones_are_not_stored():
    assert not set(REDUNDANT) & {e.id for e in CATALOG}


def test_fred_is_the_main_source_for_the_us():
    for entry in CATALOG:
        if entry.country == "US" and entry.id not in NON_FRED_ALLOWED:
            assert entry.source == "fred", entry.id


def test_api_returns_the_display_name_and_the_official_title(client, ingested):  # noqa: F811
    [series] = client.get("/v1/macro/series").json()
    assert series["name"] == "Unemployment Rate"
    assert series["concept"] == "unemployment_rate"
    assert series["title"] == "Unemployment Rate"  # official title, for the tooltip
    assert series["explanation"].endswith(".")


def test_indices_use_their_standard_name_with_the_acronym_first():
    expected = {
        "consumer_prices": "CPI – Consumer Price Index",
        "producer_prices": "PPI – Producer Price Index",
        "real_gdp": "GDP – Real Gross Domestic Product",
        "nonfarm_payrolls": "NFP – Nonfarm Payrolls",
    }
    for key, name in expected.items():
        assert CONCEPTS[key].name == name


def test_consumer_price_series_are_all_lagging_indicators():
    for series_id in ("CPIAUCSL", "CPILFESL", "CUSR0000SAS"):
        assert next(e for e in CATALOG if e.id == series_id).cycle == "lagging"


def test_every_series_has_a_business_cycle_and_a_reason_for_ours():
    from app.data.cycle_classification import QUFIN_CYCLE

    for entry in CATALOG:
        assert entry.cycle in ("leading", "coincident", "lagging"), f"{entry.id} has no cycle"
    ids = {e.id for e in CATALOG}
    assert set(QUFIN_CYCLE) <= ids, "a classification for a series not in the catalog"
    for series_id, (cycle, reason) in QUFIN_CYCLE.items():
        assert reason.endswith("."), series_id
        assert next(e for e in CATALOG if e.id == series_id).cycle == cycle


def test_the_api_reports_a_cycle_for_every_series(client, ingested):  # noqa: F811
    for series in client.get("/v1/macro/series").json():
        assert series["cycle"] in ("leading", "coincident", "lagging"), series["id"]


def test_acronym_names_use_the_global_acronym_and_its_full_name():
    for key, concept in CONCEPTS.items():
        if concept.acronym is None:
            continue
        full = concept.name.split(" – ", 1)[1]
        assert ACRONYMS.get(concept.acronym) == full, f"{key}: '{concept.name}' is not in ACRONYMS"
    assert {c.acronym for c in CONCEPTS.values() if c.acronym} <= set(ACRONYMS)


def test_local_names_never_replace_the_global_indicator_name():
    import re

    for key, concept in CONCEPTS.items():
        for alias, global_name in LOCAL_ALIASES.items():
            assert not re.search(rf"{re.escape(alias)}", concept.name), (
                f"{key}: use {global_name}, not the local name {alias}"
            )


def test_every_country_maps_its_own_version_to_the_one_global_concept():
    # The euro area's HICP and the US CPI are the same indicator to QuFin: one concept key.
    keys = {(e.country, SERIES_CONCEPTS[(e.country, e.id)]) for e in CATALOG}
    assert ("EA", "consumer_prices") in keys and ("US", "consumer_prices") in keys
    assert CONCEPTS["consumer_prices"].acronym == "CPI"


def test_api_returns_the_global_acronym(client, ingested):  # noqa: F811
    [series] = client.get("/v1/macro/series").json()
    assert "acronym" in series
