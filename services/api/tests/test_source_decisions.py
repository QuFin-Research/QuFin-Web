"""Source history and score versioning (rules 16, P and 20).

A country-indicator pair is served by one source at a time. A change is a dated source decision:
the old series is retired and kept for as-of reads, the new one serves from the change date, and
past scores do not move.
"""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.indicator_concepts import SERIES_CONCEPTS
from app.domain.versioning import SCORECARD_VERSION, catalog_version
from app.jobs.check_data import check_macro
from app.jobs.scorecard import indicator_statuses
from app.stores.macro import OPEN_END, MacroStore, SeriesMeta, Vintage
from app.stores.source_decisions import CONFIRMED, PROVISIONAL, SourceStore
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

OLD, NEW = "OLDCPI", "CPIAUCSL"  # NEW is in the catalog; OLD is the source it replaced
CHANGE = date(2025, 6, 1)


def months(first, count):
    return [
        date(first.year + (first.month - 1 + i) // 12, (first.month - 1 + i) % 12 + 1, 1)
        for i in range(count)
    ]


def put(session, series_id, periods, value=lambda i: 100 + (i % 9) * 1.7 + i * 0.31, source="fred"):
    MacroStore(session).replace_series(
        SeriesMeta(
            id=series_id,
            source=source,
            title=f"{series_id} (test)",
            units="Index 1982-1984=100",
            frequency="Monthly",
            seasonal_adjustment="Seasonally Adjusted",
            country="US",
            dimension="inflation",
            last_updated=None,
            cycle="lagging",
        ),
        [Vintage(p, p + timedelta(days=15), OPEN_END, value(i)) for i, p in enumerate(periods)],
    )
    session.commit()


def decide_change(session):
    sources = SourceStore(session)
    sources.decide("US", "consumer_prices", OLD, "fred", date(2020, 1, 1), reason="first")
    return sources.decide(
        "US", "consumer_prices", NEW, "eurostat", CHANGE, reason="earlier release (rule P)"
    )


# --- the decisions ----------------------------------------------------------------------------


def test_a_change_ends_the_open_decision_and_retires_its_series(db_session):
    put(db_session, OLD, months(date(2020, 1, 1), 60))
    put(db_session, NEW, months(date(2020, 1, 1), 70))
    decide_change(db_session)
    sources = SourceStore(db_session)
    first, second = sources.history("US", "consumer_prices")
    assert first.effective_to == CHANGE and second.effective_to is None
    assert sources.in_force("US", "consumer_prices", date(2025, 5, 31)).series_id == OLD
    assert sources.in_force("US", "consumer_prices", CHANGE).series_id == NEW
    assert sources.in_force("US", "consumer_prices", date(2019, 1, 1)) is None
    served = {s.meta.id for s in MacroStore(db_session).list_series()}
    assert NEW in served and OLD not in served  # a retired series is never served as current
    both = {s.meta.id for s in MacroStore(db_session).list_series(("live", "retired"))}
    assert {OLD, NEW} <= both


def test_a_decision_cannot_start_before_the_one_it_replaces_or_repeat_itself(db_session):
    sources = SourceStore(db_session)
    sources.decide("US", "consumer_prices", OLD, "fred", CHANGE, reason="first")
    with pytest.raises(ValueError, match="before"):
        sources.decide("US", "consumer_prices", NEW, "ons", date(2024, 1, 1), reason="x")
    with pytest.raises(ValueError, match="already serves"):
        sources.decide("US", "consumer_prices", OLD, "fred", CHANGE, reason="x")
    with pytest.raises(ValueError, match="status"):
        sources.decide("US", "consumer_prices", NEW, "ons", CHANGE, reason="x", status="maybe")


def test_a_provisional_decision_serves_and_is_confirmed_by_the_measurement(db_session):
    sources = SourceStore(db_session)
    sources.decide(
        "US", "consumer_prices", NEW, "fred", CHANGE, reason="latest period", status=PROVISIONAL
    )
    assert sources.in_force("US", "consumer_prices", CHANGE).status == PROVISIONAL
    sources.confirm("US", "consumer_prices")
    assert sources.in_force("US", "consumer_prices", CHANGE).status == CONFIRMED


def test_a_staged_series_is_never_served(db_session):
    put(db_session, "STAGEDCPI", months(date(2024, 1, 1), 30))
    SourceStore(db_session).stage("STAGEDCPI")
    assert "STAGEDCPI" not in {s.meta.id for s in MacroStore(db_session).list_series()}
    assert "STAGEDCPI" in {s.meta.id for s in MacroStore(db_session).list_series(("staged",))}


# --- rule 16: the duplicate check ---------------------------------------------------------------


def _reason(session, series_id):
    checks = {c.id: c.status.freshness for c in check_macro(session, date(2025, 10, 1))}
    return checks[series_id].reason


def test_a_retired_series_may_match_its_successor_but_nothing_else(db_session):
    periods = months(date(2020, 1, 1), 70)
    put(db_session, OLD, periods)
    put(db_session, NEW, periods)  # the same values: the new source's history overlaps the old
    put(db_session, "UNRATE", periods)  # another pair that also carries those values
    assert "OLDCPI" in _reason(db_session, NEW)  # before any decision it is a plain duplicate

    decide_change(db_session)
    assert "OLDCPI" not in _reason(db_session, NEW)  # expected overlap with its own predecessor
    # ...but the retired series is still compared with every other pair's series.
    assert "OLDCPI" in _reason(db_session, "UNRATE")


# --- as-of reads ----------------------------------------------------------------------------------


def test_a_source_change_does_not_alter_what_an_earlier_date_reads(db_session):
    put(db_session, OLD, months(date(2020, 1, 1), 62))  # ends Feb 2025
    put(db_session, NEW, months(date(2020, 1, 1), 70))  # ends Oct 2025
    sources = SourceStore(db_session)
    assert sources.series_in_force(NEW, "US", date(2025, 5, 1)) == NEW  # no decision yet
    decide_change(db_session)
    assert sources.series_in_force(NEW, "US", date(2025, 5, 1)) == OLD
    assert sources.series_in_force(NEW, "US", date(2025, 7, 1)) == NEW
    assert sources.series_in_force("UNRATE", "US", date(2025, 5, 1)) == "UNRATE"  # other pair

    store = MacroStore(db_session)

    def last_period(as_of):
        status = next(s for s in indicator_statuses(store, as_of) if s.score.id == NEW)
        return status.last_period

    assert last_period(date(2025, 5, 1)) == date(2025, 2, 1)  # the retired series, as then
    assert last_period(date(2025, 10, 1)) == date(2025, 9, 1)  # the new one from the change on


# --- rule 20: versions ----------------------------------------------------------------------------


def test_the_catalog_version_changes_with_a_source_decision_and_only_then(db_session):
    before = catalog_version(db_session)
    assert before == catalog_version(db_session)  # stable
    SourceStore(db_session).decide(
        "US", "consumer_prices", OLD, "fred", date(2020, 1, 1), reason="first", status=PROVISIONAL
    )
    provisional = catalog_version(db_session)
    assert provisional != before  # a provisional decision counts
    SourceStore(db_session).confirm("US", "consumer_prices")
    assert catalog_version(db_session) not in (before, provisional)


def test_a_live_score_says_which_scorecard_and_catalog_made_it(client, ingested, db_session):
    [us] = client.get("/v1/scorecards/countries", params={"asOf": "2026-10-10"}).json()
    assert us["scorecardVersion"] == SCORECARD_VERSION
    assert us["catalogVersion"] == catalog_version(db_session)
    assert us["mechanism"] == "hidden"  # the versions are shown even when the recipe is hidden
    assert datetime.now(UTC)  # (keeps the import used)


# --- the commands ---------------------------------------------------------------------------------


def test_the_commands_record_list_confirm_and_stage(db_session, capsys, monkeypatch):
    from contextlib import contextmanager

    from app import cli

    monkeypatch.setattr(cli, "upgrade_to_head", lambda _engine: None)
    monkeypatch.setattr(cli, "get_engine", lambda: None)

    @contextmanager
    def scope():
        yield db_session

    monkeypatch.setattr(cli, "session_scope", scope)
    base = ["source-decision", "--country", "US", "--concept", "consumer_prices"]
    assert (
        cli.main(
            [
                *base,
                "--series",
                OLD,
                "--source",
                "fred",
                "--reason",
                "first",
                "--from",
                "2020-01-01",
                "--provisional",
            ]
        )
        == 0
    )
    assert cli.main([*base, "--confirm"]) == 0
    assert (
        cli.main(
            [
                *base,
                "--series",
                NEW,
                "--source",
                "eurostat",
                "--reason",
                "earlier",
                "--from",
                "2025-06-01",
            ]
        )
        == 0
    )
    assert cli.main([*base, "--series", NEW]) == 2  # needs --source and --reason
    assert (
        cli.main([*base, "--series", NEW, "--source", "x", "--reason", "y", "--from", "2025-06-01"])
        == 2
    )  # already serves
    assert cli.main(["source-history", "--country", "US"]) == 0
    assert cli.main(["catalog-version"]) == 0
    out = capsys.readouterr().out
    assert "OLDCPI [fred] 2020-01-01 -> 2025-06-01 (confirmed)" in out
    assert "CPIAUCSL [eurostat] 2025-06-01 -> now" in out
    assert f"scorecard {SCORECARD_VERSION}, catalog " in out


# --- rule 20: scores as shown ---------------------------------------------------------------------


def test_each_distinct_live_score_shown_is_kept_and_repeats_are_not(client, ingested, db_session):
    from app.stores.score_snapshots import SnapshotStore

    for _ in range(3):
        [us] = client.get("/v1/scorecards/countries", params={"asOf": "2026-10-10"}).json()
    shown = SnapshotStore(db_session).shown("US", date(2026, 10, 10))
    assert len(shown) == 1  # served three times, kept once
    assert shown[0]["scorecard_version"] == SCORECARD_VERSION
    assert shown[0]["catalog_version"] == us["catalogVersion"]
    assert "indicators" not in shown[0]  # the recipe is never stored


def test_a_changed_score_is_kept_beside_the_one_shown_before(client, ingested, db_session):
    from app.schemas.market import CountryScores
    from app.stores.score_snapshots import SnapshotStore

    [us] = client.get("/v1/scorecards/countries", params={"asOf": "2026-10-10"}).json()
    store = SnapshotStore(db_session)
    from app.schemas.market import CountryScore

    card = CountryScore.model_validate(us)
    changed = card.model_copy(
        update={"scores": CountryScores(growth=1.0, inflation=0, labour=0, policy=0, sentiment=0)}
    )
    assert store.record(changed) is True
    assert store.record(changed) is False
    assert len(store.shown("US", date(2026, 10, 10))) == 2


def test_sample_scores_and_scores_without_versions_are_not_kept(db_session):
    from app.data.repository import SampleMarketRepository
    from app.stores.score_snapshots import SnapshotStore

    sample = SampleMarketRepository().get_country_scores()[0]
    assert SnapshotStore(db_session).record(sample) is False


def _cli_on(db_session, monkeypatch):
    from contextlib import contextmanager

    from app import cli

    monkeypatch.setattr(cli, "upgrade_to_head", lambda _engine: None)
    monkeypatch.setattr(cli, "get_engine", lambda: None)

    @contextmanager
    def scope():
        yield db_session

    monkeypatch.setattr(cli, "session_scope", scope)
    return cli


def test_the_baseline_switches_every_eurostat_pair_once_and_keeps_the_old_series(
    db_session, monkeypatch, capsys
):
    from app.data.macro_catalog import BY_ID
    from app.data.source_baseline import BASELINE, PREDECESSORS

    for b in BASELINE:
        assert b.series_id in BY_ID and BY_ID[b.series_id].source == b.source
        assert SERIES_CONCEPTS[(b.country, b.series_id)] == b.concept
        if b.predecessor:
            assert b.predecessor.series_id not in BY_ID  # no longer declared beside it
    assert len(BASELINE) == 37 and len(PREDECESSORS) == 35  # Kosovo and US property: no predecessor

    put(db_session, "IMF_CPI_DEU", months(date(2020, 1, 1), 60), source="imf")
    put(db_session, "ESTAT_HICP_DE", months(date(2020, 1, 1), 62), source="eurostat")
    cli = _cli_on(db_session, monkeypatch)
    assert cli.main(["source-decision", "--baseline"]) == 0
    assert cli.main(["source-decision", "--baseline"]) == 0
    out = capsys.readouterr().out
    assert "baseline: 37 decisions recorded, 0 already there" in out
    assert "baseline: 0 decisions recorded, 37 already there" in out

    old, new = SourceStore(db_session).history("DE", "consumer_prices")
    assert old.series_id == "IMF_CPI_DEU" and old.effective_to == new.effective_from
    assert new.series_id == "ESTAT_HICP_DE" and new.status == PROVISIONAL
    sources = SourceStore(db_session)
    assert sources.in_force("DE", "consumer_prices", date(2026, 11, 18)).series_id == "IMF_CPI_DEU"
    assert (
        sources.in_force("DE", "consumer_prices", date(2026, 11, 19)).series_id == "ESTAT_HICP_DE"
    )
    served = {s.meta.id for s in MacroStore(db_session).list_series()}
    assert "ESTAT_HICP_DE" in served and "IMF_CPI_DEU" not in served  # retired, not served
    assert MacroStore(db_session).as_of("IMF_CPI_DEU")  # but its history is still there


def test_a_pair_already_switched_once_is_closed_and_switched_again(db_session, monkeypatch):
    """Portugal was FRED's copy of HICP from 18 Nov 2026; the baseline moves it to Eurostat."""
    SourceStore(db_session).decide(
        "PT",
        "consumer_prices",
        "CP0000PTM086NEST",
        "fred",
        date(2026, 11, 18),
        reason="FRED copy of the HICP, chosen when FRED was first",
        status=PROVISIONAL,
    )
    assert _cli_on(db_session, monkeypatch).main(["source-decision", "--baseline"]) == 0
    first, second = SourceStore(db_session).history("PT", "consumer_prices")
    assert first.series_id == "CP0000PTM086NEST" and first.effective_to == date(2026, 11, 19)
    assert second.series_id == "ESTAT_HICP_PT"


def test_the_pruning_keeps_the_series_a_switch_retires_and_still_removes_other_strays(db_session):
    from app.jobs.ingest_fred import prune

    put(db_session, "IMF_CPI_DEU", months(date(2020, 1, 1), 30), source="imf")
    put(db_session, "STRAYSERIES", months(date(2020, 1, 1), 30))
    assert prune(db_session) == ["STRAYSERIES"]
    assert MacroStore(db_session).get_series("IMF_CPI_DEU") is not None


def test_a_retired_series_gives_up_its_canonical_code_to_the_series_that_replaces_it(db_session):
    """The canonical code is unique per live series, so the new series can be loaded."""
    from sqlalchemy import select

    from app.stores.macro import MacroSeriesRow

    put(db_session, OLD, months(date(2020, 1, 1), 40))
    row = db_session.get(MacroSeriesRow, OLD)
    row.canonical_code = "USA.INF.CPI.M.NSA"
    db_session.commit()
    sources = SourceStore(db_session)
    sources.decide("US", "consumer_prices", OLD, "fred", date(2020, 1, 1), reason="first")
    sources.decide("US", "consumer_prices", NEW, "eurostat", CHANGE, reason="earlier")
    db_session.expire_all()
    assert db_session.get(MacroSeriesRow, OLD).canonical_code is None
    put(db_session, NEW, months(date(2020, 1, 1), 40))
    new = db_session.scalars(select(MacroSeriesRow).where(MacroSeriesRow.id == NEW)).one()
    new.canonical_code = "USA.INF.CPI.M.NSA"
    db_session.commit()  # no unique violation


def test_the_six_economies_level_with_eurostat_went_to_it_by_the_native_tie_break():
    from app.data.source_baseline import BASELINE

    tied = {b.country: b for b in BASELINE if b.reason.startswith("Tie at the 19 Nov 2026 probe")}
    assert set(tied) == {"AL", "BE", "CH", "EE", "LU", "SI"}
    assert all("more native source" in b.reason for b in tied.values())
    assert all(
        b.predecessor and b.predecessor.series_id.startswith("IMF_CPI_") for b in tied.values()
    )
