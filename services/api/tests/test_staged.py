"""Rule 38, staging: candidate sources are loaded and timed, never served, scored or compared."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.connectors.sdmx import SdmxError
from app.data.candidates import CANDIDATES, PREFIX, Candidate
from app.data.macro_catalog import BY_ID
from app.jobs import refresh
from app.jobs.ingest_staged import ingest, prune_staged, staging_due, stale_staged
from app.stores.candidates import CandidateStore
from app.stores.macro import MacroStore, SeriesMeta
from tests.staging import DE
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

FRA = Candidate(
    **{
        **DE.__dict__,
        "id": "CAND_IMF_CPI_FRA",
        "country": "FR",
        "area": "FRA",
        "serves": "ESTAT_HICP_FR",
        "key": DE.key.replace("DEU", "FRA"),
    }
)
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


def test_the_registry_holds_no_economy_eurostat_serves_and_names_the_series_it_is_timed_against():
    from app.domain.source_selection import bloc_aggregator_of

    # rule 38 (v3.5): nothing is timed for an economy Eurostat serves
    timed = [c for c in CANDIDATES if c.serves]
    assert timed and all(bloc_aggregator_of(c.country) is None for c in timed)
    assert all(c.id.startswith(PREFIX) and BY_ID[c.serves].country == c.country for c in timed)
    [property_prices] = [c for c in timed if c.concept == "commercial_property_prices"]
    assert (property_prices.source, property_prices.serves) == ("fred", "BIS_CPP_US")
    assert property_prices.months == 3 and property_prices.key == "COMREPUSQ159N"


def test_a_candidate_is_never_a_catalog_series_and_names_the_series_it_is_timed_against():
    for c in (DE, FRA):
        assert c.id.startswith(PREFIX) and c.id not in BY_ID
        assert c.concept == "consumer_prices" and c.source == "imf" and c.producer == "global"
        assert BY_ID[c.serves].source == "eurostat"
        assert c.key.startswith(f"{c.area}.CPI.")


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
    other = FRA
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
    assert not staging_due(db_session, TODAY, [DE.id])  # nothing staged yet
    ingest({"imf": FakeImf(months(30))}, db_session, [DE], today=TODAY)
    today = datetime.now(UTC).date()
    assert not staging_due(db_session, today, [DE.id])  # loaded today: not again (rule 28)
    assert staging_due(db_session, today + timedelta(days=1), [DE.id])
    # a staged series no candidate names is not loaded again
    assert not staging_due(db_session, today + timedelta(days=1), [])


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


# --- staged series no candidate names -----------------------------------------------------------


def test_staged_series_no_candidate_names_are_found_and_removed_with_their_first_reads(db_session):
    ingest({"imf": FakeImf(months(30))}, db_session, [DE, FRA], today=TODAY)
    assert stale_staged(db_session, [DE.id]) == [FRA.id]  # FRA is no longer a candidate
    assert stale_staged(db_session, [DE.id, FRA.id]) == []
    assert prune_staged(db_session, [FRA.id]) == 1
    store = MacroStore(db_session)
    assert store.lifecycle_of(FRA.id) is None and store.lifecycle_of(DE.id) == "staged"
    assert CandidateStore(db_session).sightings(FRA.id) == []
    assert len(CandidateStore(db_session).sightings(DE.id)) == 30  # the others are untouched


def test_only_staged_series_can_be_pruned(db_session):
    _live = MacroStore(db_session)
    from tests.test_measurement import _serve_hicp_de

    _serve_hicp_de(db_session, date(2026, 11, 18))
    assert prune_staged(db_session, ["ESTAT_HICP_DE"]) == 0  # a served series is never touched
    assert _live.lifecycle_of("ESTAT_HICP_DE") == "live"


# --- a FRED candidate, quarterly, dated by its own first vintage ---------------------------------


class FakeFred:
    def __init__(self, vintages, fail=False):
        self._vintages, self.fail = vintages, fail

    def series(self, series_id):
        from types import SimpleNamespace

        if self.fail:
            from app.connectors.fred import FredError

            raise FredError(f"FRED has no series {series_id}")
        return SimpleNamespace(
            title="Commercial real estate prices",
            units="Percent change",
            frequency="Quarterly",
            seasonal_adjustment="Not Seasonally Adjusted",
            last_updated=None,
        )

    def vintages(self, series_id, start):
        return self._vintages


def _vintage(period, start, value, end=date(9999, 12, 31)):
    from app.stores.macro import Vintage

    return Vintage(period, start, end, value)


CPP = Candidate(
    id="CAND_FRED_CPP_US",
    country="US",
    concept="commercial_property_prices",
    source="fred",
    producer="bloc",
    area="US",
    serves="BIS_CPP_US",
    flow="",
    key="COMREPUSQ159N",
    months=3,
)


def test_a_fred_candidate_is_staged_with_its_current_values_and_first_vintage_dates(db_session):
    q1, q2 = date(2025, 10, 1), date(2026, 1, 1)
    fred = FakeFred(
        [
            _vintage(q1, date(2026, 1, 20), 1.0, date(2026, 4, 9)),
            _vintage(q1, date(2026, 4, 10), 1.5),  # revised: the current value is 1.5
            _vintage(q2, date(2026, 10, 1), 2.0),
            _vintage(date(2026, 4, 1), date(2026, 10, 1), None),  # no value: skipped
        ]
    )
    [r] = ingest({"fred": fred}, db_session, [CPP], today=TODAY)
    assert r.error is None and r.rows == 2
    store = MacroStore(db_session)
    assert store.lifecycle_of(CPP.id) == "staged"
    [summary] = [s for s in store.list_series(("staged",)) if s.meta.id == CPP.id]
    assert summary.meta.frequency == "Quarterly" and summary.last_period == q2
    assert len(CandidateStore(db_session).sightings(CPP.id)) == 2


def test_a_fred_candidate_that_fails_is_reported_not_raised(db_session):
    [r] = ingest({"fred": FakeFred([], fail=True)}, db_session, [CPP], today=TODAY)
    assert r.error and "no series" in r.error
    assert MacroStore(db_session).lifecycle_of(CPP.id) is None


def test_a_source_without_a_loader_is_reported(db_session):
    odd = Candidate(**{**CPP.__dict__, "source": "bis"})
    [r] = ingest({"bis": object()}, db_session, [odd], today=TODAY)
    assert r.error == "no loader for source bis"


# --- the BLS candidates for the US series FRED serves --------------------------------------------


def test_every_bls_candidate_names_a_us_series_fred_serves_and_its_own_bls_id():
    from app.data.indicator_concepts import SERIES_CONCEPTS

    bls = [c for c in CANDIDATES if c.source == "bls"]
    assert len(bls) == 11 and len({c.key for c in bls}) == 11
    for c in bls:
        served = BY_ID[c.serves]
        assert served.source == "fred" and served.country == c.country == "US"
        assert c.producer == "original" and c.id.startswith(PREFIX) and c.id not in BY_ID
        assert c.concept == SERIES_CONCEPTS[("US", c.serves)]
    assert {c.serves: c.months for c in bls}["ECIALLCIV"] == 3  # quarterly


class FakeBls:
    def __init__(self, observations):
        self.observations = observations
        self.asked = []

    def series(self, series_id, start_year=2000, end_year=None):
        self.asked.append((series_id, start_year))
        return self.observations


UNRATE = next(c for c in CANDIDATES if c.serves == "UNRATE")


def _store_served(session):
    MacroStore(session).replace_series(
        SeriesMeta(
            "UNRATE",
            "fred",
            "Unemployment Rate",
            "Percent",
            "Monthly",
            "Seasonally Adjusted",
            country="US",
            dimension="labour",
            last_updated=None,
            cycle="lagging",
        ),
        [_vintage(date(2026, 9, 1), date(2026, 10, 2), 4.1)],
    )


def test_a_bls_candidate_is_described_like_the_series_it_is_timed_against(db_session):
    _store_served(db_session)
    bls = FakeBls([(date(2026, 8, 1), 4.0), (date(2026, 9, 1), 4.1), (date(2026, 7, 1), None)])
    [r] = ingest({"bls": bls}, db_session, [UNRATE], today=TODAY)
    assert (
        r.error is None and r.rows == 2 and bls.asked == [(UNRATE.key, 1990)]
    )  # the default start
    store = MacroStore(db_session)
    assert store.lifecycle_of(UNRATE.id) == "staged"
    meta = store.get_series(UNRATE.id)
    assert meta.source == "bls" and meta.frequency == "Monthly" and meta.dimension == "labour"
    assert "BLS candidate" in meta.title
    assert store.lifecycle_of("UNRATE") == "live"  # the served series is untouched


def test_a_bls_candidate_is_not_loaded_while_the_series_it_describes_is_missing(db_session):
    [r] = ingest({"bls": FakeBls([(date(2026, 9, 1), 4.1)])}, db_session, [UNRATE], today=TODAY)
    assert r.error and "UNRATE is not stored" in r.error
    assert MacroStore(db_session).lifecycle_of(UNRATE.id) is None


# --- gap candidates: published by a source, held by nobody, timed against nothing ---------------


def _gaps():
    from app.data.candidates import GAP_CANDIDATES

    return GAP_CANDIDATES


def test_the_gap_candidates_are_the_probes_findings_and_describe_themselves():
    gaps = _gaps()
    # 80 until batch B (22 Nov 2026) served Eurostat's core HICP and 29 of its 30 production series
    assert len(gaps) == 18 and len({c.id for c in gaps}) == 18
    by = {}
    for c in gaps:
        by.setdefault((c.concept, c.source), []).append(c)
        assert c.serves == "" and c.id.startswith(PREFIX) and c.id not in BY_ID
        assert c.title and c.units and c.adjustment and c.dimension and c.cycle
    assert {k: len(v) for k, v in by.items()} == {
        ("industrial_production", "eurostat"): 1,  # Belgium: a month behind the rest
        ("core_consumer_prices", "oecd"): 1,
        ("industrial_production", "oecd"): 6,
        ("money_supply", "oecd"): 10,
    }
    belgium = next(c for c in gaps if c.id == "CAND_ESTAT_IP_BE")
    assert belgium.area == "BE" and "geo=BE" in belgium.key


def test_a_gap_candidate_is_for_an_economy_nothing_holds_a_series_of():
    """The pair is a gap today; once a series serves it, the candidate has done its job."""
    from app.data.indicator_concepts import SERIES_CONCEPTS

    held = {
        (country, concept) for (country, sid), concept in SERIES_CONCEPTS.items() if sid in BY_ID
    }
    assert not [c.id for c in _gaps() if (c.country, c.concept) in held]


class FakeEurostat:
    def __init__(self, fail=()):
        self.fail, self.asked = set(fail), []

    def series(self, dataset, filters, start):
        from app.connectors.eurostat import EurostatError

        self.asked.append((dataset, dict(filters)))
        if filters["geo"] in self.fail:
            raise EurostatError("Eurostat returned no observations")
        return SimpleNamespace(observations=[(date(2026, 8, 1), 1.5), (date(2026, 9, 1), 1.6)])


def _gap(candidate_id):
    return next(c for c in _gaps() if c.id == candidate_id)


def test_a_eurostat_gap_candidate_is_staged_with_its_own_description(db_session):
    fe = FakeEurostat()
    [r] = ingest({"eurostat": fe}, db_session, [_gap("CAND_ESTAT_IP_BE")], today=TODAY)
    assert r.error is None and r.rows == 2
    assert fe.asked == [
        (
            "sts_inpr_m",
            {
                "freq": "M",
                "indic_bt": "PRD",
                "nace_r2": "B-D",
                "s_adj": "SCA",
                "unit": "I21",
                "geo": "BE",
            },
        )
    ]
    store = MacroStore(db_session)
    assert store.lifecycle_of("CAND_ESTAT_IP_BE") == "staged"
    meta = store.get_series("CAND_ESTAT_IP_BE")
    assert meta.country == "BE" and meta.dimension == "growth" and meta.cycle == "coincident"
    assert "candidate" in meta.title and meta.units == "Index, 2021=100"
    assert len(CandidateStore(db_session).sightings("CAND_ESTAT_IP_BE")) == 2


def test_an_oecd_gap_candidate_uses_its_own_key_and_a_missing_one_is_reported(db_session):
    class Oecd:
        def __init__(self):
            self.asked = []

        def series(self, flow, key, start):
            self.asked.append((flow, key))
            return SimpleNamespace(
                observations=[(date(2026, 8, 1), 100.0), (date(2026, 9, 1), None)]
            )

    oecd = Oecd()
    [r] = ingest({"oecd": oecd}, db_session, [_gap("CAND_OECD_MONEY_GBR")], today=TODAY)
    assert r.error is None and r.rows == 1  # a month with no value is not stored
    assert oecd.asked == [("OECD.SDD.STES,DSD_STES@DF_MONAGG,", "GBR.M.MABM.XDC._Z.Y._Z._Z.N")]
    [bad] = ingest(
        {"eurostat": FakeEurostat(fail=["BE"])}, db_session, [_gap("CAND_ESTAT_IP_BE")], today=TODAY
    )
    assert bad.error and MacroStore(db_session).lifecycle_of("CAND_ESTAT_IP_BE") is None


def test_gap_candidates_are_not_timed_and_no_decision_is_asked_of_them(db_session):
    from app.jobs.decide_sources import plan
    from app.jobs.measure_candidates import measure_all

    gaps = _gaps()
    assert measure_all(db_session, gaps, TODAY) == []  # nothing to be timed against
    assert plan(db_session, gaps, TODAY) == []


def _bis_oecd_gaps():
    from app.data.candidates import BIS_GAP_CANDIDATES, OECD_SURVEY_GAP_CANDIDATES

    return [*BIS_GAP_CANDIDATES, *OECD_SURVEY_GAP_CANDIDATES]


def test_the_second_sweeps_gap_candidates_describe_themselves_and_leave_eurostats_economies():
    from app.domain.source_selection import bloc_aggregator_of

    gaps = _bis_oecd_gaps()
    assert len(gaps) == 37 and len({c.id for c in gaps}) == 37
    for c in gaps:
        assert c.serves == "" and c.id.startswith(PREFIX) and c.id not in BY_ID and c.measure
        assert c.title and c.units and c.adjustment and c.dimension and c.cycle and "{" not in c.key
        if c.concept in {
            "residential_property_prices",
            "business_confidence",
            "consumer_sentiment",
            "unemployment_rate",
        }:
            assert bloc_aggregator_of(c.country) is None  # Eurostat's to serve (rule 38)
    from app.data.indicator_concepts import SERIES_CONCEPTS

    held = {
        (country, concept) for (country, sid), concept in SERIES_CONCEPTS.items() if sid in BY_ID
    }
    assert not [c.id for c in gaps if (c.country, c.concept) in held]
    assert {c.id for c in gaps}.isdisjoint({c.id for c in _gaps()})


def test_a_bis_gap_candidate_is_staged_with_its_measure_and_a_wrong_answer_is_reported(db_session):
    class Bis:
        def __init__(self, series):
            self.series, self.asked = series, []

        def many(self, flow, key, start, version):
            self.asked.append((flow, key, version))
            return self.series

    cand = next(c for c in _bis_oecd_gaps() if c.id == "CAND_BIS_CBTA_KR")
    from app.data.bis_ids import MEASURES

    stated = {
        "UNIT_MEASURE": MEASURES[cand.measure].unit_measure,
        "UNIT_MULT": MEASURES[cand.measure].unit_mult,
    }
    cand_unit = SimpleNamespace(
        observations=[(date(2026, 1, 1), 5.0), (date(2026, 4, 1), None)], attributes=stated
    )
    client = Bis([cand_unit])
    [r] = ingest({"bis": client}, db_session, [cand], today=TODAY)
    assert r.error is None and r.rows == 1  # a period with no value is not stored
    assert client.asked == [(cand.flow, cand.key, "1.0")]
    meta = MacroStore(db_session).get_series("CAND_BIS_CBTA_KR")
    assert meta.country == "KR" and meta.dimension == cand.dimension and "candidate" in meta.title
    assert MacroStore(db_session).lifecycle_of("CAND_BIS_CBTA_KR") == "staged"
    two = Bis([cand_unit, cand_unit])
    [bad] = ingest({"bis": two}, db_session, [cand], today=TODAY)
    assert bad.error and "expected one" in bad.error
