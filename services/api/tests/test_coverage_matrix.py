"""Coverage matrix: every country against every indicator, from the database, with real statuses."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

import csv
from datetime import date, timedelta

import pytest

from app.data.taxonomy import COUNTRIES
from app.jobs import coverage_matrix, doctor
from app.stores.macro import MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

TODAY = date(2026, 10, 20)  # a month after the last period put() stores
OPEN = date(9999, 12, 31)


def put(session, series_id="UNRATE", country="US"):
    MacroStore(session).replace_series(
        SeriesMeta(
            id=series_id,
            source="fred",
            title=f"{series_id} (test)",
            units="Percent",
            frequency="Monthly",
            seasonal_adjustment="Seasonally Adjusted",
            country=country,
            dimension="labour",
            last_updated=None,
            cycle="lagging",
        ),
        [
            Vintage(date(2026, m, 1), date(2026, m, 1) + timedelta(days=20), OPEN, 4.0 + m / 10)
            for m in range(1, 10)
        ],
    )
    session.commit()


def cell(cells, concept, iso3):
    [found] = [c for c in cells if c.concept_key == concept and c.iso3 == iso3]
    return found


def test_scope_follows_how_many_countries_an_indicator_is_declared_for():
    scopes = coverage_matrix.concept_scopes()
    assert scopes["unemployment_rate"] == ("global", None)
    assert scopes["money_supply"][0] == "global"  # the US and the euro area share it
    assert scopes["initial_jobless_claims"] == ("country_specific", "US")
    assert scopes["crude_oil_inventories"][0] == "commodity"
    assert scopes["crude_oil_wti"][0] == "market"
    assert scopes["fx_eurusd"][0] == "market"


def test_every_country_has_a_row_for_every_indicator(db_session):
    cells = coverage_matrix.build(db_session, TODAY)
    indicators = coverage_matrix.concept_scopes()
    assert len(cells) == len(COUNTRIES) * len(indicators)
    assert {c.iso3 for c in cells} == {p.iso3 for p in COUNTRIES}  # Isle of Man included


def test_a_stored_usable_series_is_have_with_its_own_source_frequency_and_dates(db_session):
    put(db_session)
    c = cell(coverage_matrix.build(db_session, TODAY), "unemployment_rate", "USA")
    assert (c.status, c.scope, c.series_id) == ("HAVE", "global", "UNRATE")
    assert (c.source, c.frequency) == ("fred", "Monthly")
    assert (c.first_period, c.last_period) == ("2026-01-01", "2026-09-01")
    assert c.pillar == "LABOR" and c.tier3_portal == ""


def test_a_stored_series_past_its_release_is_overdue_not_have(db_session):
    put(db_session)
    c = cell(coverage_matrix.build(db_session, date(2027, 6, 1)), "unemployment_rate", "USA")
    assert c.status == "OVERDUE"
    assert c.tier3_portal  # where to look for a replacement


def test_a_declared_series_that_is_not_stored_is_not_loaded_and_a_missing_one_is_a_gap(db_session):
    cells = coverage_matrix.build(db_session, TODAY)
    declared = cell(cells, "unemployment_rate", "DEU")  # the catalog lists the OECD series
    assert declared.status == "NOT_LOADED" and declared.series_id.startswith("OECD_UNE_")
    missing = cell(cells, "unemployment_rate", "IMN")  # no source declared for the Isle of Man
    assert missing.status == "GAP" and missing.series_id == ""
    assert missing.pillar == "LABOR"  # a gap still says which pillar the indicator belongs to
    assert missing.tier3_portal


def test_an_indicator_one_country_owns_is_not_applicable_everywhere_else(db_session):
    cells = coverage_matrix.build(db_session, TODAY)
    assert cell(cells, "initial_jobless_claims", "DEU").status == "NOT_APPLICABLE"
    assert cell(cells, "initial_jobless_claims", "USA").status == "NOT_LOADED"
    assert cell(cells, "crude_oil_inventories", "FRA").status == "NOT_APPLICABLE"


def test_coverage_counts_only_global_indicators(db_session):
    put(db_session)
    summary = coverage_matrix.summarize(coverage_matrix.build(db_session, TODAY))
    global_indicators = summary.scopes["global"]
    assert summary.applicable == global_indicators * len(COUNTRIES)
    assert summary.have == 1  # the one series stored
    assert summary.by_status["NOT_APPLICABLE"] > summary.by_status["GAP"]  # the US-only majority
    text = coverage_matrix.format_summary(summary)
    assert "coverage of global indicators: 1 of" in text


def test_every_pair_the_doctor_calls_unpopulated_is_a_gap_or_not_loaded_here(db_session):
    put(db_session)
    cells = coverage_matrix.build(db_session, TODAY)
    for g in doctor.unpopulated_pairs(db_session):
        assert cell(cells, g.concept, g.iso3).status in ("GAP", "NOT_LOADED"), g


def test_the_csv_has_one_row_per_cell_and_the_documented_columns(db_session, tmp_path):
    put(db_session)
    cells = coverage_matrix.build(db_session, TODAY)
    path = tmp_path / "matrix.csv"
    coverage_matrix.write_csv(cells, path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(cells)
    assert list(rows[0]) == [
        "concept_key", "indicator", "iso3", "country", "scope", "status", "series_id",
        "source", "frequency", "first_period", "last_period", "pillar", "tier3_portal",
    ]  # fmt: skip
    assert {r["status"] for r in rows} <= set(coverage_matrix.STATUSES)


def test_the_coverage_matrix_command_is_registered():
    from app.cli import main

    with pytest.raises(SystemExit) as stop:
        main(["coverage-matrix", "--help"])
    assert stop.value.code == 0
