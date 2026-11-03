"""The indicator catalog rules (services/api/CLAUDE.md, rules 16-18). Do not loosen these."""

from collections import Counter

from app.data.indicator_concepts import CONCEPTS, REDUNDANT, SERIES_CONCEPTS, concept_for
from app.data.macro_catalog import CATALOG
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

# US series that may come from a source other than FRED, with the reason (rule: FRED first).
NON_FRED_ALLOWED: dict[str, str] = {}


def test_every_series_has_a_display_name_and_plain_explanation():
    for entry in CATALOG:
        concept = concept_for(entry.country, entry.id)
        assert concept is not None, f"{entry.id} has no display name"
        assert concept.name and len(concept.name) <= 40, entry.id
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
