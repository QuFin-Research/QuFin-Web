"""QuFin Doctor (Rule N): each check finds its fault, and --fix repairs only what is safe."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.data.taxonomy import COUNTRIES
from app.jobs import doctor
from app.stores.macro import MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

TODAY = date(2026, 11, 13)
OPEN = date(9999, 12, 31)


def put(session, series_id, country="US", adjustment="Seasonally Adjusted", frequency="Monthly"):
    MacroStore(session).replace_series(
        SeriesMeta(
            id=series_id,
            source="fred",
            title=f"{series_id} (test)",
            units="Percent",
            frequency=frequency,
            seasonal_adjustment=adjustment,
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


def found(report, check):
    return [f for f in report.findings if f.check == check]


def test_a_clean_series_raises_none_of_the_per_series_checks(db_session):
    put(db_session, "UNRATE")
    report = doctor.run(db_session, TODAY)
    for check in ("orphaned vintages", "non-finite values", "vintage dates", "SA/NSA tag"):
        assert found(report, check) == [], check


def test_orphaned_vintages_are_found_and_deleted_only_with_fix(db_session):
    put(db_session, "UNRATE")
    db_session.execute(
        text(
            "INSERT INTO macro_observations VALUES ('GONE', '2026-01-01', '2026-02-01', "
            "'9999-12-31', 1.0)"
        )
    )
    db_session.commit()
    assert found(doctor.run(db_session, TODAY), "orphaned vintages")[0].detail == "1 rows"
    repaired = doctor.run(db_session, TODAY, fix=True)
    assert found(repaired, "orphaned vintages")[0].fixed
    assert found(doctor.run(db_session, TODAY), "orphaned vintages") == []
    remaining = db_session.execute(
        text("SELECT COUNT(*) FROM macro_observations WHERE series_id = 'UNRATE'")
    ).scalar()
    assert remaining == 9  # the healthy series was not touched


def test_values_that_are_not_finite_are_found_and_removed_with_fix(db_session):
    put(db_session, "UNRATE")
    db_session.execute(
        text(
            "UPDATE macro_observations SET value = 1e309 WHERE series_id = 'UNRATE' "
            "AND period = '2026-03-01'"
        )
    )
    db_session.commit()
    assert found(doctor.run(db_session, TODAY), "non-finite values")
    assert found(doctor.run(db_session, TODAY, fix=True), "non-finite values")[0].fixed
    assert found(doctor.run(db_session, TODAY), "non-finite values") == []


def test_reversed_and_overlapping_vintages_are_flagged_never_repaired(db_session):
    put(db_session, "UNRATE")
    db_session.execute(
        text(
            "UPDATE macro_observations SET realtime_start = '2026-12-01', realtime_end = "
            "'2026-11-01' WHERE series_id = 'UNRATE' AND period = '2026-01-01'"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO macro_observations VALUES ('UNRATE', '2026-02-01', '2026-02-10', "
            "'9999-12-31', 9.9)"
        )
    )
    db_session.commit()
    report = doctor.run(db_session, TODAY, fix=True)
    messages = " ".join(f.detail for f in found(report, "vintage dates"))
    assert "start after they end" in messages and "overlap" in messages
    assert not any(f.fixed for f in found(report, "vintage dates"))
    quick = doctor.run(db_session, TODAY, quick=True)  # the overlap scan is the slow one
    assert "overlap" not in " ".join(f.detail for f in found(quick, "vintage dates"))


def test_two_series_for_one_country_and_indicator_are_a_duplicate(db_session, monkeypatch):
    put(db_session, "UNRATE")
    put(db_session, "ICSA")
    monkeypatch.setitem(SERIES_CONCEPTS, ("US", "ICSA"), SERIES_CONCEPTS[("US", "UNRATE")])
    dup = found(doctor.run(db_session, TODAY), "duplicate indicator")
    assert len(dup) == 1 and "UNRATE (fred)" in dup[0].detail and "ICSA (fred)" in dup[0].detail
    assert not dup[0].fixed  # which one to keep is a person's decision (Rule M)


def test_a_series_without_an_adjustment_tag_is_an_error(db_session):
    put(db_session, "UNRATE", adjustment=" ")
    assert found(doctor.run(db_session, TODAY), "SA/NSA tag")[0].subject == "UNRATE"


def test_a_stale_canonical_code_is_rederived_with_fix(db_session):
    put(db_session, "UNRATE")
    db_session.execute(
        text("UPDATE macro_series SET canonical_code = 'USA.LABOR.UNEMPLOYMENT_RATE.M.NSA'")
    )
    db_session.commit()
    assert found(doctor.run(db_session, TODAY), "canonical code")
    assert found(doctor.run(db_session, TODAY, fix=True), "canonical code")[0].fixed
    assert found(doctor.run(db_session, TODAY), "canonical code") == []


def test_series_outside_the_catalog_are_removed_with_fix(db_session):
    put(db_session, "NOT_IN_CATALOG")
    report = doctor.run(db_session, TODAY)
    assert found(report, "stale series")[0].subject == "NOT_IN_CATALOG"
    assert found(doctor.run(db_session, TODAY, fix=True), "stale series")[0].fixed
    assert MacroStore(db_session).get_series("NOT_IN_CATALOG") is None


def test_every_catalog_series_missing_from_the_database_is_an_error(db_session):
    report = doctor.run(db_session, TODAY)
    assert "never been ingested" in found(report, "missing series")[0].detail


def test_a_series_past_its_release_window_is_reported_as_frozen_with_the_way_out(db_session):
    put(db_session, "UNRATE")
    report = doctor.run(db_session, TODAY + timedelta(days=400))
    frozen = found(report, "frozen or overdue")
    assert frozen[0].subject == "UNRATE" and "quarantine" in frozen[0].detail


def test_the_taxonomy_must_hold_all_87_countries_and_countries_without_data_are_listed(
    db_session,
):
    assert len(COUNTRIES) == doctor.EXPECTED_COUNTRIES == 87
    put(db_session, "UNRATE")
    report = doctor.run(db_session, TODAY)
    assert found(report, "country taxonomy") == []
    warning = found(report, "country data")[0]
    assert (
        warning.level == "warning"
        and "Germany" in warning.detail
        and "United States" not in (warning.detail)
    )


def test_a_file_database_is_backed_up_before_a_destructive_fix(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.stores.db import Base

    path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        put(session, "UNRATE")
        session.execute(
            text(
                "INSERT INTO macro_observations VALUES ('GONE', '2026-01-01', '2026-02-01', "
                "'9999-12-31', 1.0)"
            )
        )
        session.commit()
        report = doctor.run(session, TODAY, fix=True)
    assert report.backup is not None and report.backup.exists()
    assert report.backup.name.startswith("test.doctor-") and report.backup.suffix == ".db"
    assert "backup" in doctor.format_report(report)


def test_the_report_says_when_the_database_is_healthy_and_how_many_problems_otherwise():
    assert doctor.format_report(doctor.DoctorReport([], None)).endswith("healthy")
    report = doctor.DoctorReport(
        [
            doctor.Finding("orphaned vintages", "error", "t", "1 rows"),
            doctor.Finding("country data", "warning", "50 countries", "none"),
            doctor.Finding("stale series", "warning", "X", "stored", True),
        ],
        None,
    )
    assert "1 errors, 1 warnings" in doctor.format_report(report)
    assert "FIXED" in doctor.format_report(report)


@pytest.mark.parametrize("command", ["doctor", "ingest-eurostat", "ingest-ons"])
def test_the_commands_are_registered(command):
    from app.cli import main

    with pytest.raises(SystemExit) as stop:
        main([command, "--help"])
    assert stop.value.code == 0


def test_unpopulated_pairs_list_the_tier_3_portal_and_the_check_date(db_session, monkeypatch):
    # Eight countries hold unemployment, so it counts as a widely held indicator.
    for n, country in enumerate(["US", "GB", "FR", "IT", "JP", "CA", "AU", "KR"]):
        series_id = f"T{n}"
        put(db_session, series_id, country=country)
        monkeypatch.setitem(SERIES_CONCEPTS, (country, series_id), "unemployment_rate")
    gaps = doctor.unpopulated_pairs(db_session)
    germany = next(g for g in gaps if g.iso3 == "DEU")
    assert germany.indicator == "Unemployment Rate" and germany.registered == date(2026, 11, 13)
    assert "Destatis GENESIS" in germany.portal and "terms not yet read" in germany.portal
    assert not any(g.iso3 == "USA" for g in gaps)  # the US holds it
    iceland = next(g for g in gaps if g.iso3 == "ISL")
    assert iceland.registered is None and "UNECE" in iceland.portal  # no national portal registered
    report = doctor.run(db_session, TODAY)
    summary = found(report, "unpopulated pairs")[0]
    assert summary.level == "warning" and "doctor --gaps" in summary.detail
    text = doctor.format_gaps(gaps)
    assert "Germany" in text and "unpopulated pairs" in text.splitlines()[-1]


def test_no_gap_is_reported_when_nothing_is_widely_held(db_session):
    put(db_session, "UNRATE")  # one country is not a widely held indicator
    assert doctor.unpopulated_pairs(db_session) == []
    assert "no unpopulated" in doctor.format_gaps([])
    assert found(doctor.run(db_session, TODAY), "unpopulated pairs") == []
