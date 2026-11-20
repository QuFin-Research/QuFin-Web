"""Rule 38, staging: candidate sources are loaded and timed, never served, scored or compared."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.connectors.sdmx import SdmxError
from app.data.candidates import CANDIDATE_BY_ID, CANDIDATES, PREFIX
from app.data.macro_catalog import BY_ID
from app.jobs import refresh
from app.jobs.ingest_staged import ingest, staging_due
from app.stores.candidates import CandidateStore
from app.stores.macro import MacroStore, SeriesMeta
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

DE = CANDIDATE_BY_ID["CAND_IMF_CPI_DEU"]
TODAY = date(2026, 11, 20)


def months(count, last=date(2026, 9, 1)):
    end = last.year * 12 + last.month - 1
    return [date((end - i) // 12, (end - i) % 12 + 1, 1) for i in reversed(range(count))]


class FakeImf:
    """Stands in for the IMF client: no network."""

    def __init__(self, periods, fail=()):
        self.periods, self.fail, self.asked = periods, set(fail), []

    def series(self, flow, key, start):
        self.asked.append(key)
        if any(f in key for f in self.fail):
            raise SdmxError("the IMF has no such series")
        return SimpleNamespace(observations=[(p, 2.0 + i / 10) for i, p in enumerate(self.periods)])


# --- the registry ---------------------------------------------------------------------------------


def test_the_candidates_are_the_imf_series_that_served_the_provisional_consumer_price_pairs():
    assert len(CANDIDATES) == 32
    assert len({c.id for c in CANDIDATES}) == 32
    for c in CANDIDATES:
        assert c.id.startswith(PREFIX) and c.id not in BY_ID  # never a catalog series
        assert c.concept == "consumer_prices" and c.source == "imf" and c.producer == "global"
        assert BY_ID[c.serves].source == "eurostat"  # the series it is timed against
        assert c.key.startswith(f"{c.area}.CPI.")
    assert {"DEU", "FRA", "ISL", "TUR"} <= {c.area for c in CANDIDATES}
    assert "PRT" not in {c.area for c in CANDIDATES}  # Portugal's was FRED's copy, not the IMF


# --- loading without serving ----------------------------------------------------------------------


def _live_hicp_de(session):
    """The series that serves the pair, holding the canonical code a candidate must not take."""
    MacroStore(session).record_latest(
        SeriesMeta(
            "ESTAT_HICP_DE",
            "eurostat",
            "HICP, all items: annual rate of change, DE",
            "Percentage change",
            "Monthly",
            "Not Seasonally Adjusted",
            "DE",
            "inflation",
            None,
            "lagging",
        ),
        [(p, 2.9) for p in months(30)],
        lambda p: p + timedelta(days=45),
        TODAY,
    )


def test_a_candidate_is_staged_and_never_takes_the_code_of_the_series_that_serves_the_pair(
    db_session,
):
    _live_hicp_de(db_session)
    live = MacroStore(db_session).get_series("ESTAT_HICP_DE")
    assert live.canonical_code
    [result] = ingest({"imf": FakeImf(months(30))}, db_session, [DE], today=TODAY)
    assert result.error is None and result.rows == 30
    store = MacroStore(db_session)
    assert store.lifecycle_of(DE.id) == "staged"
    assert store.get_series(DE.id).canonical_code is None
    assert store.get_series("ESTAT_HICP_DE").canonical_code == live.canonical_code
    assert DE.id not in {s.meta.id for s in store.list_series()}  # not served
    assert DE.id in {s.meta.id for s in store.list_series(("staged",))}


def test_the_api_never_serves_a_staged_series(client, db_session):
    ingest({"imf": FakeImf(months(30))}, db_session, [DE], today=TODAY)
    assert client.get(f"/v1/macro/series/{DE.id}").status_code == 404
    assert DE.id not in {
        s["seriesId"] if "seriesId" in s else s["id"] for s in client.get("/v1/macro/series").json()
    }


def test_one_candidate_that_fails_does_not_stop_the_others(db_session):
    other = CANDIDATE_BY_ID["CAND_IMF_CPI_FRA"]
    results = ingest(
        {"imf": FakeImf(months(30), fail=["DEU"])}, db_session, [DE, other], today=TODAY
    )
    assert [r.error is None for r in results] == [False, True]
    assert MacroStore(db_session).lifecycle_of(other.id) == "staged"


# --- the days first read ---------------------------------------------------------------------


def test_the_day_each_period_was_first_read_is_kept_and_the_first_load_is_not_timing(db_session):
    ingest({"imf": FakeImf(months(30))}, db_session, [DE], today=TODAY)
    sightings = CandidateStore(db_session)
    assert len(sightings.sightings(DE.id)) == 30
    assert all(s.bootstrap and s.first_seen == TODAY for s in sightings.sightings(DE.id))
    assert sightings.measurable(DE.id) == []  # published before QuFin looked

    later = TODAY + timedelta(days=12)  # the IMF publishes October
    ingest({"imf": FakeImf(months(31, date(2026, 10, 1)))}, db_session, [DE], today=later)
    [october] = sightings.measurable(DE.id)
    assert october.period == date(2026, 10, 1) and october.first_seen == later
    assert not october.bootstrap
    ingest({"imf": FakeImf(months(31, date(2026, 10, 1)))}, db_session, [DE], today=later)
    assert len(sightings.sightings(DE.id)) == 31  # a period is first read once


# --- the refresh -----------------------------------------------------------------------------


def test_the_staging_step_is_planned_only_when_candidates_are_stored_and_not_loaded_today(
    db_session,
):
    assert not staging_due(db_session, TODAY)  # nothing staged yet
    ingest({"imf": FakeImf(months(30))}, db_session, [DE], today=TODAY)
    today = datetime.now(UTC).date()
    assert not staging_due(db_session, today)  # loaded today: not again (rule 28)
    assert staging_due(db_session, today + timedelta(days=1))


class _Done:
    def __init__(self, code, out):
        self.returncode, self.stdout, self.stderr = code, out, ""


@pytest.mark.parametrize(("code", "status"), [(0, "ok"), (1, "overdue")])
def test_a_staging_failure_is_reported_and_never_fails_the_refresh(monkeypatch, code, status):
    out = "staged: 30 of 32 candidates loaded"
    monkeypatch.setattr(refresh.subprocess, "run", lambda *a, **k: _Done(code, out))
    step = refresh.Step(refresh.STAGING_COMMAND, "staging", ())
    result = refresh.subprocess_executor(step, 5)
    assert result.status == status and "30 of 32" in result.detail
