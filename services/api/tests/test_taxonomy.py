"""Canonical taxonomy, point-in-time queries by code, the economic calendar (ADR 0007)."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import UTC, date, datetime

import pytest

from app.data import taxonomy
from app.data.benchmarks import BENCHMARK_SERIES
from app.data.indicator_concepts import SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID, CATALOG, Dimension
from app.domain.surprise import MIN_HISTORY, surprise, surprise_score
from app.jobs import build_calendar, sync_taxonomy
from app.stores.macro import MacroSeriesRow, MacroStore
from app.stores.point_in_time import PointInTime, SeriesNotFoundError, known_through
from app.stores.taxonomy import CountryRow, EconomicEventRow
from tests.test_macro_api import db_session, ingested  # noqa: F401  (fixtures)

UNRATE_CODE = "USA.LABOR.UNEMPLOYMENT_RATE.M.SA"


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


# --- the taxonomy -------------------------------------------------------------------------------


def test_the_canonical_code_has_five_parts_from_country_pillar_indicator_frequency_adjustment():
    code = taxonomy.canonical_code("UNRATE", "US", "Monthly", "Seasonally Adjusted")
    assert code == UNRATE_CODE
    assert taxonomy.parse_code(code) == ("USA", "LABOR", "UNEMPLOYMENT_RATE", "M", "SA")
    with pytest.raises(taxonomy.TaxonomyError):
        taxonomy.parse_code("USA.LABOR.UNRATE")


def test_a_series_outside_the_catalog_has_no_code():
    assert taxonomy.canonical_code("NOT_A_SERIES", "US", "Monthly", "Seasonally Adjusted") is None


def test_every_seasonal_adjustment_the_sources_state_has_a_code_and_an_unknown_one_fails():
    for text, code in [
        ("Not Seasonally Adjusted", "NSA"),
        ("Seasonally Adjusted", "SA"),
        ("Seasonally Adjusted Annual Rate", "SAAR"),
        ("Amplitude Adjusted (OECD)", "AA"),
        ("Seasonally and Working Day Adjusted", "SWDA"),
    ]:
        assert taxonomy.adjustment_code(text) == code
    with pytest.raises(taxonomy.TaxonomyError):
        taxonomy.adjustment_code("Smoothed by hand")


@pytest.mark.parametrize(
    ("units", "scale"),
    [
        ("Millions of Dollars", 1e6),
        ("Billions of Chained 2017 Dollars", 1e9),
        ("Thousands of Persons", 1e3),
        ("Level in Thousands", 1e3),
        ("Thousand Barrels per Day", 1e3),
        ("Percent", 1.0),
        ("Index, 2020=100", 1.0),
        ("Dollars per Million BTU", 1.0),  # "Million" here is part of the unit, not its scale
    ],
)
def test_scale_is_read_from_the_start_of_the_units_text(units, scale):
    assert taxonomy.scale_of(units) == scale


def test_every_catalog_dimension_maps_to_a_pillar_and_all_eight_pillars_are_used():
    assert set(taxonomy.DIMENSION_PILLAR) == set(Dimension.__args__)  # type: ignore[attr-defined]
    used = {taxonomy.pillar_for(s.country, s.id) for s in CATALOG}
    assert set(taxonomy.PILLARS) <= used
    assert used <= set(taxonomy.PILLARS) | set(taxonomy.REFERENCE_CLASSES)


def test_indicators_filed_under_the_wrong_dimension_get_their_real_pillar():
    pillar = taxonomy.pillar_for
    assert pillar("US", "UMCSENT") == "SURVEYS"
    assert pillar("US", "RRSFS") == "CONSUMPTION"
    assert pillar("US", "NFCI") == "MONETARY"
    assert pillar("US", "CIS1010000000000I") == "LABOR"  # employment cost index, was external


def test_every_catalog_country_is_in_the_taxonomy_and_codes_are_unique_in_it():
    assert {s.country for s in CATALOG} <= set(taxonomy.COUNTRY_BY_ISO2)
    assert len({c.iso3 for c in taxonomy.COUNTRIES}) == len(taxonomy.COUNTRIES)
    assert len({c.iso2 for c in taxonomy.COUNTRIES}) == len(taxonomy.COUNTRIES)
    # the G7, and the six Gulf states
    assert {c.iso3 for c in taxonomy.COUNTRIES if c.g7} == {
        "USA", "GBR", "JPN", "CAN", "DEU", "FRA", "ITA"
    }  # fmt: skip
    assert {c.iso3 for c in taxonomy.COUNTRIES if c.gcc} == {
        "SAU", "ARE", "KWT", "QAT", "BHR", "OMN"
    }  # fmt: skip


def test_the_fifteen_benchmarks_are_distinct_catalog_series_across_g20_and_gcc():
    assert len(BENCHMARK_SERIES) == len(set(BENCHMARK_SERIES)) == 15
    countries = {BY_ID[sid].country for sid in BENCHMARK_SERIES}
    assert all(sid in BY_ID for sid in BENCHMARK_SERIES)
    assert {"US", "EA", "GB", "JP", "CN", "IN", "BR", "SA"} <= countries
    assert all(
        (BY_ID[sid].country, sid) in SERIES_CONCEPTS for sid in BENCHMARK_SERIES
    )  # each has a name (rule 18)


# --- coding the stored series -----------------------------------------------------------------


def test_ingest_stores_code_pillar_and_scale_with_the_series(db_session, ingested):
    row = db_session.get(MacroSeriesRow, "UNRATE")
    assert (row.canonical_code, row.pillar, row.scale) == (UNRATE_CODE, "LABOR", 1.0)


def test_sync_fills_countries_and_is_idempotent(db_session, ingested):
    first = sync_taxonomy.sync(db_session)
    assert first.countries == len(taxonomy.COUNTRIES)
    assert db_session.get(CountryRow, "SAU").gcc is True
    assert sync_taxonomy.sync(db_session).changed == 0


def test_sync_repairs_a_series_stored_before_the_taxonomy_existed(db_session, ingested):
    row = db_session.get(MacroSeriesRow, "UNRATE")
    row.canonical_code = row.pillar = None
    db_session.commit()
    assert sync_taxonomy.sync(db_session).changed == 1
    assert db_session.get(MacroSeriesRow, "UNRATE").canonical_code == UNRATE_CODE


def test_an_unknown_adjustment_wording_loads_the_series_uncoded_and_sync_reports_it(
    db_session, ingested
):
    store = MacroStore(db_session)
    meta = store.get_series("UNRATE")
    store.replace_series(
        type(meta)(**{**meta.__dict__, "seasonal_adjustment": "Smoothed by hand"}), []
    )
    assert db_session.get(MacroSeriesRow, "UNRATE").canonical_code is None  # loaded, not lost
    assert sync_taxonomy.sync(db_session).uncoded == ("UNRATE",)


def test_the_eia_states_short_adjustment_codes_and_they_are_accepted():
    assert taxonomy.adjustment_code("NSA") == "NSA"
    assert taxonomy.adjustment_code("SA") == "SA"


def test_two_series_with_one_code_are_a_duplicate_and_fail(db_session, ingested, monkeypatch):
    store = MacroStore(db_session)
    meta = store.get_series("UNRATE")
    store.replace_series(
        type(meta)(**{**meta.__dict__, "id": "UNRATE2", "canonical_code": None}), []
    )
    monkeypatch.setattr(sync_taxonomy, "canonical_code", lambda *_a: "USA.LABOR.X.M.SA")
    with pytest.raises(taxonomy.TaxonomyError, match="belongs to both"):
        sync_taxonomy.sync(db_session)


# --- point in time ----------------------------------------------------------------------------
# UNRATE: August first printed 4.3 on 5 Sep 2026, revised to 4.2 on 3 Oct, when September was
# first printed at 4.1 (tests/test_macro_api.py).


def values(series):
    return {o.period: o.value for o in series.observations}


def test_a_vintage_dated_d_is_known_from_the_next_day():
    assert known_through(utc(2026, 10, 3, 0, 0)) == date(2026, 10, 2)
    assert known_through(utc(2026, 10, 3, 23, 59)) == date(2026, 10, 2)
    assert known_through(utc(2026, 10, 4)) == date(2026, 10, 3)
    # a timestamp in another zone is read in UTC
    assert known_through(datetime.fromisoformat("2026-10-04T01:00:00+03:00")) == date(2026, 10, 2)


def test_before_the_revision_the_series_shows_the_first_print_not_the_revised_value(
    db_session,
    ingested,
):
    earlier = PointInTime(db_session).get_point_in_time_series(UNRATE_CODE, utc(2026, 9, 20, 12))
    assert values(earlier) == {date(2026, 8, 1): 4.3}  # September had not been published
    assert earlier.known_through == date(2026, 9, 19)


def test_after_the_revision_it_shows_the_revised_value_and_the_new_period(db_session, ingested):
    later = PointInTime(db_session).get_point_in_time_series(UNRATE_CODE, utc(2026, 10, 10))
    assert values(later) == {date(2026, 8, 1): 4.2, date(2026, 9, 1): 4.1}


def test_the_day_of_the_revision_does_not_yet_see_it(db_session, ingested):
    pit = PointInTime(db_session)
    on_the_day = pit.get_point_in_time_series(UNRATE_CODE, utc(2026, 10, 3, 18))
    assert values(on_the_day) == {date(2026, 8, 1): 4.3}  # err late: no look-ahead
    next_day = pit.get_point_in_time_series(UNRATE_CODE, utc(2026, 10, 4))
    assert values(next_day)[date(2026, 8, 1)] == 4.2


def test_before_anything_was_published_the_series_is_empty(db_session, ingested):
    assert (
        not PointInTime(db_session)
        .get_point_in_time_series(UNRATE_CODE, utc(2026, 9, 1))
        .observations
    )


def test_the_latest_series_has_the_newest_vintage_of_every_period(db_session, ingested):
    latest = PointInTime(db_session).get_latest_series(UNRATE_CODE)
    assert values(latest) == {date(2026, 8, 1): 4.2, date(2026, 9, 1): 4.1}
    assert latest.as_of is None and latest.known_through is None
    only_sep = PointInTime(db_session).get_latest_series(UNRATE_CODE, start_date=date(2026, 9, 1))
    assert list(values(only_sep)) == [date(2026, 9, 1)]


def test_each_observation_says_when_it_was_published(db_session, ingested):
    latest = PointInTime(db_session).get_latest_series(UNRATE_CODE)
    assert {o.period: o.vintage_date for o in latest.observations} == {
        date(2026, 8, 1): date(2026, 10, 3),
        date(2026, 9, 1): date(2026, 10, 3),
    }


def test_an_unknown_code_is_not_found(db_session, ingested):
    with pytest.raises(SeriesNotFoundError):
        PointInTime(db_session).get_latest_series("USA.LABOR.NOTHING.M.SA")


def test_only_the_united_states_has_pillar_scores_and_others_say_not_scored(db_session, ingested):
    pit = PointInTime(db_session)
    usa = pit.compute_macro_pillar_scores("USA", utc(2026, 10, 10))
    by_pillar = {p.pillar: p for p in usa.pillars}
    assert list(by_pillar) == list(taxonomy.PILLARS)
    for unscored in ("TRADE", "CONSUMPTION", "FISCAL"):
        assert by_pillar[unscored].status == "not_scored_yet"
        assert by_pillar[unscored].score is None
    assert by_pillar["LABOR"].status in ("scored", "no_usable_data")
    saudi = pit.compute_macro_pillar_scores("SAU", utc(2026, 10, 10))
    assert {p.status for p in saudi.pillars} == {"not_scored_yet"}
    assert saudi.overall is None and saudi.overall_confidence == 0.0
    with pytest.raises(LookupError):
        pit.compute_macro_pillar_scores("XXX", utc(2026, 10, 10))


# --- surprise ---------------------------------------------------------------------------------


def test_surprise_needs_a_consensus_and_enough_history_and_is_never_estimated():
    assert surprise(4.2, None) is None
    assert surprise(4.2, 4.0) == pytest.approx(0.2)
    history = [0.1, -0.1] * (MIN_HISTORY // 2)
    assert surprise_score(4.2, None, history) is None
    assert surprise_score(4.2, 4.0, history[:3]) is None
    assert surprise_score(4.2, 4.0, [0.0] * MIN_HISTORY) is None  # no spread, no score
    assert surprise_score(4.2, 4.0, history) == pytest.approx(2.0)  # 0.2 over a 0.1 spread


# --- the calendar -----------------------------------------------------------------------------

TODAY = date(2026, 11, 12)


def events(db_session):
    rows = db_session.query(EconomicEventRow).order_by(EconomicEventRow.period).all()
    return {r.period: r for r in rows}


def test_released_events_carry_the_first_print_and_the_previous_value_known_then(
    db_session,
    ingested,
):
    result = build_calendar.build(db_session, TODAY)
    assert (result.released, result.scheduled) == (2, 1)
    by_period = events(db_session)
    august, september = by_period[date(2026, 8, 1)], by_period[date(2026, 9, 1)]
    assert (august.status, august.release_date, august.actual_value) == (
        "released",
        date(2026, 9, 5),
        4.3,  # the first print, not the later 4.2
    )
    assert august.previous_value is None  # no July in the store
    assert (september.release_date, september.actual_value) == (date(2026, 10, 3), 4.1)
    assert september.previous_value == 4.2  # August as known on 3 Oct, after its revision


def test_the_next_release_is_scheduled_by_the_usual_lag_and_nothing_is_invented(
    db_session,
    ingested,
):
    build_calendar.build(db_session, TODAY)
    october = events(db_session)[date(2026, 10, 1)]
    assert october.status == "scheduled"
    assert october.release_date == date(2026, 11, 4)  # September + 31 days + the median 33-day lag
    assert october.previous_value == 4.1
    assert october.actual_value is None
    assert october.consensus_estimate is None and october.surprise_score is None


def test_rebuilding_changes_nothing_and_keeps_a_consensus_a_feed_supplied(db_session, ingested):
    build_calendar.build(db_session, TODAY)
    september = events(db_session)[date(2026, 9, 1)]
    september.consensus_estimate, september.consensus_source = 4.0, "licensed feed"
    db_session.commit()
    build_calendar.build(db_session, TODAY)
    assert db_session.query(EconomicEventRow).count() == 3
    again = events(db_session)[date(2026, 9, 1)]
    assert (again.consensus_estimate, again.consensus_source) == (4.0, "licensed feed")
    assert again.surprise_score is None  # a single past event is too little history


def test_a_release_becomes_released_when_its_period_lands(db_session, ingested):
    build_calendar.build(db_session, date(2026, 10, 10))
    assert events(db_session)[date(2026, 10, 1)].status == "scheduled"
    assert events(db_session)[date(2026, 10, 1)].release_time_utc is None


# --- the endpoints ----------------------------------------------------------------------------


def test_countries_endpoint_lists_blocs_and_the_series_per_pillar(ingested, client):
    countries = {c["iso3"]: c for c in client.get("/v1/macro/countries").json()}
    assert countries["USA"]["seriesCount"] == 1
    assert countries["USA"]["pillars"] == {"LABOR": 1}
    assert countries["SAU"]["gcc"] is True and countries["SAU"]["seriesCount"] == 0
    assert all(c["data"] == "live" for c in countries.values())


def test_indicators_endpoint_lists_each_indicator_once_with_its_countries(ingested, client):
    [indicator] = client.get("/v1/macro/indicators").json()
    assert indicator["name"] == "Unemployment Rate"
    assert indicator["pillar"] == "LABOR"
    assert indicator["countries"] == ["USA"]


def test_code_endpoint_returns_the_latest_or_the_series_as_known_then(ingested, client):
    latest = client.get(f"/v1/macro/code/{UNRATE_CODE}").json()
    assert latest["seriesId"] == "UNRATE" and latest["asOf"] is None
    assert [o["value"] for o in latest["observations"]] == [4.2, 4.1]
    early = client.get(f"/v1/macro/code/{UNRATE_CODE}", params={"asOf": "2026-09-20T12:00:00Z"})
    assert [o["value"] for o in early.json()["observations"]] == [4.3]
    by_day = client.get(f"/v1/macro/code/{UNRATE_CODE}", params={"asOf": "2026-10-03"})
    assert [o["value"] for o in by_day.json()["observations"]] == [4.2, 4.1]  # a day is inclusive


def test_code_endpoint_validates_and_404s(ingested, client):
    assert client.get("/v1/macro/code/USA.LABOR.NOTHING.M.SA").status_code == 404
    assert client.get("/v1/macro/code/not-a-code").status_code == 422
    bad = client.get(f"/v1/macro/code/{UNRATE_CODE}", params={"asOf": "yesterday"})
    assert bad.status_code == 422
    dates = {"start": "2026-09-01", "end": "2026-08-01"}
    assert client.get(f"/v1/macro/code/{UNRATE_CODE}", params=dates).status_code == 422


def test_pillar_scores_endpoint(ingested, client):
    usa = client.get("/v1/macro/pillar-scores/USA").json()
    assert [p["pillar"] for p in usa["pillars"]] == list(taxonomy.PILLARS)
    assert client.get("/v1/macro/pillar-scores/SAU").json()["overall"] is None
    assert client.get("/v1/macro/pillar-scores/XXX").status_code == 404
    assert client.get("/v1/macro/pillar-scores/us").status_code == 422


def test_calendar_endpoint_filters_by_window_country_and_pillar(db_session, ingested, client):
    build_calendar.build(db_session, date(2026, 11, 1))
    rows = client.get(
        "/v1/macro/calendar", params={"from": "2026-09-01", "to": "2026-11-30"}
    ).json()
    assert [(r["period"], r["status"]) for r in rows] == [
        ("2026-08-01", "released"),
        ("2026-09-01", "released"),
        ("2026-10-01", "scheduled"),
    ]
    assert rows[0]["consensusEstimate"] is None and rows[0]["canonicalCode"] == UNRATE_CODE
    one_day = client.get("/v1/macro/calendar", params={"from": "2026-10-03", "to": "2026-10-03"})
    assert [r["period"] for r in one_day.json()] == ["2026-09-01"]
    other = {"from": "2026-09-01", "to": "2026-11-30", "country": "JPN"}
    assert client.get("/v1/macro/calendar", params=other).json() == []
    labor = {"from": "2026-09-01", "to": "2026-11-30", "pillar": "LABOR"}
    assert len(client.get("/v1/macro/calendar", params=labor).json()) == 3
    assert (
        client.get(
            "/v1/macro/calendar", params={"from": "2026-12-01", "to": "2026-11-01"}
        ).status_code
        == 422
    )
    assert client.get("/v1/macro/calendar", params={"country": "ZZZ"}).status_code == 404


def test_series_list_now_carries_code_pillar_and_iso3(ingested, client):
    [summary] = client.get("/v1/macro/series").json()
    assert summary["canonicalCode"] == UNRATE_CODE
    assert summary["pillar"] == "LABOR" and summary["countryIso3"] == "USA"
