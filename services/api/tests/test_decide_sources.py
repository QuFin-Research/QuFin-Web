"""Rule 38: from a measurement to a decision, and the move of a winner into the catalog."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date
from types import SimpleNamespace

import pytest

from app.data.macro_catalog import BY_ID
from app.jobs import promote as promote_module
from app.jobs.decide_sources import CONFIRM, NO_DECISION, REPLACE, SETTLED, WAIT, apply, plan
from app.jobs.ingest_staged import ingest
from app.jobs.promote import PromotionError, promote
from app.stores.candidates import CandidateStore
from app.stores.macro import MacroStore
from app.stores.source_decisions import CONFIRMED, PROVISIONAL, SourceStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)
from tests.test_measurement import DE, OCT, FakeImf, _serve_hicp_de

SEP = date(2026, 9, 1)
EUROSTAT_READ = date(2026, 11, 18)


def staged_pair(session, *, decision=True, staged_on=date(2026, 11, 5)):
    """Eurostat serves Germany (October first read on 18 Nov); the IMF candidate is staged with
    September already published, so October is the first period that can time it."""
    _serve_hicp_de(session, EUROSTAT_READ)
    if decision:
        SourceStore(session).decide(
            "DE",
            "consumer_prices",
            "ESTAT_HICP_DE",
            "eurostat",
            date(2026, 11, 19),
            reason="Eurostat held October",
            status=PROVISIONAL,
        )
    ingest({"imf": FakeImf(SEP)}, session, [DE], today=staged_on)


def imf_publishes_october(session, on):
    ingest({"imf": FakeImf(OCT)}, session, [DE], today=on)


def _vintage_rows(session, series_id):
    from sqlalchemy import func, select

    from app.stores.macro import MacroObservationRow

    return session.scalar(
        select(func.count())
        .select_from(MacroObservationRow)
        .where(MacroObservationRow.series_id == series_id)
    )


def loaded(**days):
    return {"CAND_IMF_CPI_DEU": days["candidate"], "ESTAT_HICP_DE": days["served"]}


# --- what a measurement means ----------------------------------------------------------


def test_nothing_is_decided_while_the_candidate_has_published_nothing(db_session):
    staged_pair(db_session)
    now = date(2026, 11, 22)
    [o] = plan(db_session, [DE], now, loaded(candidate=now, served=now))
    assert o.action == WAIT and "has not published" in o.why  # a lower bound is not a measurement


def test_a_slower_candidate_confirms_the_provisional_decision_and_apply_records_it(db_session):
    staged_pair(db_session)
    imf_publishes_october(db_session, date(2026, 11, 27))
    now = date(2026, 11, 28)
    [o] = plan(db_session, [DE], now, loaded(candidate=now, served=now))
    assert o.action == CONFIRM and o.measurement.verdict == "served earlier"
    assert SourceStore(db_session).in_force("DE", "consumer_prices", now).status == PROVISIONAL

    assert [x.candidate.id for x in apply(db_session, [o])] == [DE.id]
    assert SourceStore(db_session).in_force("DE", "consumer_prices", now).status == CONFIRMED
    [again] = plan(db_session, [DE], now, loaded(candidate=now, served=now))
    assert again.action == SETTLED  # measured again each cycle: still the earliest


def test_a_faster_candidate_is_a_replacement_that_apply_never_makes(db_session):
    staged_pair(db_session)
    imf_publishes_october(
        db_session, date(2026, 11, 12)
    )  # the IMF read it six days before Eurostat
    now = date(2026, 11, 28)
    [o] = plan(db_session, [DE], now, loaded(candidate=now, served=now))
    assert o.action == REPLACE and o.measurement.verdict == "candidate earlier"
    assert apply(db_session, [o]) == []  # a change of source is a reviewed pull request
    assert (
        SourceStore(db_session).in_force("DE", "consumer_prices", now).series_id == "ESTAT_HICP_DE"
    )


def test_a_pair_with_no_decision_for_the_series_serving_it_is_left_alone(db_session):
    staged_pair(db_session, decision=False)
    imf_publishes_october(db_session, date(2026, 11, 27))
    now = date(2026, 11, 28)
    [o] = plan(db_session, [DE], now, loaded(candidate=now, served=now))
    assert o.action == NO_DECISION and apply(db_session, [o]) == []


# --- promoting a winner ----------------------------------------------------------------


@pytest.fixture
def winner(db_session, monkeypatch):
    """The IMF was earlier and a reviewed pull request added its series to the catalog."""
    staged_pair(db_session)
    imf_publishes_october(db_session, date(2026, 11, 12))
    entry = SimpleNamespace(source="imf", country="DE", dimension="inflation")
    monkeypatch.setitem(BY_ID, "IMF_CPI_DEU_2", entry)
    return db_session


def test_a_winner_takes_its_staged_history_and_retires_the_series_it_replaces(winner):
    staged_obs = _vintage_rows(winner, DE.id)  # every value and every revision of it
    current = len(MacroStore(winner).as_of(DE.id))
    staged_reads = len(CandidateStore(winner).sightings(DE.id))
    done = promote(winner, DE.id, "IMF_CPI_DEU_2", date(2026, 12, 1), reason="IMF read it first")
    assert (done.observations, done.sightings, done.retired) == (
        staged_obs,
        staged_reads,
        "ESTAT_HICP_DE",
    )
    store = MacroStore(winner)
    assert store.lifecycle_of("IMF_CPI_DEU_2") == "live" and store.lifecycle_of(DE.id) is None
    assert _vintage_rows(winner, "IMF_CPI_DEU_2") == staged_obs  # nothing re-fetched, nothing lost
    assert len(store.as_of("IMF_CPI_DEU_2")) == current
    reads = CandidateStore(winner).measurable("IMF_CPI_DEU_2")
    assert [r.period for r in reads] == [OCT] and reads[0].first_seen == date(2026, 11, 12)
    sources = SourceStore(winner)
    assert (
        sources.in_force("DE", "consumer_prices", date(2026, 11, 30)).series_id == "ESTAT_HICP_DE"
    )
    now = sources.in_force("DE", "consumer_prices", date(2026, 12, 1))
    assert now.series_id == "IMF_CPI_DEU_2" and now.status == CONFIRMED
    assert store.lifecycle_of("ESTAT_HICP_DE") == "retired"
    assert store.get_series("ESTAT_HICP_DE").canonical_code is None  # the code moves on
    assert "IMF_CPI_DEU_2" in {s.meta.id for s in store.list_series()}  # served from now on


@pytest.mark.parametrize(
    ("candidate", "series", "message"),
    [
        ("CAND_NOPE", "IMF_CPI_DEU_2", "not a registered candidate"),
        ("CAND_IMF_CPI_DEU", "NOT_IN_CATALOG", "must be in the catalog"),
        ("CAND_IMF_CPI_DEU", "ESTAT_HICP_DE", "must be in the catalog with source imf"),
    ],
)
def test_a_promotion_that_cannot_be_made_safely_changes_nothing(winner, candidate, series, message):
    before = len(MacroStore(winner).as_of(DE.id))
    with pytest.raises(PromotionError, match=message):
        promote(winner, candidate, series, date(2026, 12, 1), reason="x")
    assert MacroStore(winner).lifecycle_of(DE.id) == "staged"
    assert len(MacroStore(winner).as_of(DE.id)) == before


def test_an_id_that_is_already_stored_is_refused(winner, monkeypatch):
    monkeypatch.setitem(BY_ID, "ESTAT_HICP_DE", SimpleNamespace(source="imf", country="DE"))
    with pytest.raises(PromotionError, match="already stored"):
        promote(winner, DE.id, "ESTAT_HICP_DE", date(2026, 12, 1), reason="x")


def test_a_failure_part_way_rolls_everything_back(winner, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(promote_module, "canonical_code", broken)
    with pytest.raises(RuntimeError):
        promote(winner, DE.id, "IMF_CPI_DEU_2", date(2026, 12, 1), reason="x")
    store = MacroStore(winner)
    assert store.lifecycle_of(DE.id) == "staged" and store.lifecycle_of("IMF_CPI_DEU_2") is None
    sources = SourceStore(winner)
    assert sources.in_force("DE", "consumer_prices", date(2026, 12, 1)).series_id == "ESTAT_HICP_DE"
