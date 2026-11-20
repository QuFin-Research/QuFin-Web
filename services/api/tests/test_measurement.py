"""Rule 38, "Earliest": a source's lag is measured on the same observation, over a release cycle."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

from datetime import date, timedelta

from app.data.candidates import CANDIDATE_BY_ID
from app.domain.measurement import (
    MIN_RELEASES,
    lag_days,
    measure,
    period_end,
    producer_of,
    read_period,
)
from app.jobs.ingest_staged import ingest
from app.jobs.measure_candidates import measure_all
from app.stores.macro import OPEN_END, MacroStore, SeriesMeta, Vintage
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

OCT = date(2026, 10, 1)
DE = CANDIDATE_BY_ID["CAND_IMF_CPI_DEU"]


# --- the arithmetic ----------------------------------------------------------------------


def test_a_lag_is_the_days_from_the_end_of_the_period_to_the_first_read():
    assert period_end(OCT) == date(2026, 10, 31)
    assert period_end(date(2026, 12, 1)) == date(2026, 12, 31)  # a December rolls the year
    assert period_end(date(2026, 1, 1), 3) == date(2026, 3, 31)  # a quarter
    assert lag_days(OCT, date(2026, 11, 18)) == 18


def test_how_native_a_source_is_depends_on_the_economy():
    assert producer_of("eurostat", "DE") == "bloc"
    assert producer_of("fred", "US") == "bloc" and producer_of("fred", "DE") == "global"
    assert producer_of("imf", "DE") == "global"
    assert producer_of("bls", "US") == "original"


def read(served, candidate, served_loaded=date(2026, 11, 25), candidate_loaded=date(2026, 11, 25)):
    return read_period(
        OCT,
        served_read=served,
        candidate_read=candidate,
        served_loaded=served_loaded,
        candidate_loaded=candidate_loaded,
    )


def judged(*reads):
    return measure(
        "CAND_X",
        "SERVED_X",
        [r for r in reads if r],
        served_source="eurostat",
        candidate_source="imf",
        country="DE",
        served_latest=OCT,
        candidate_latest=OCT,
    )


def test_the_series_read_first_wins_and_the_pair_is_confirmed():
    m = judged(read(date(2026, 11, 18), date(2026, 11, 25)))
    assert (m.served_median, m.candidate_median) == (18, 25)
    assert m.verdict == "served earlier" and m.recommendation == "confirm"
    assert not m.bounded


def test_a_candidate_read_first_replaces_the_series_that_serves_the_pair():
    m = judged(read(date(2026, 11, 18), date(2026, 11, 12)))
    assert m.verdict == "candidate earlier" and m.recommendation == "replace"


def test_equal_lags_go_to_the_more_native_source_the_one_that_serves_the_pair():
    m = judged(read(date(2026, 11, 18), date(2026, 11, 18)))
    assert m.verdict == "level" and m.recommendation == "confirm"  # Eurostat, a bloc, over the IMF
    flipped = measure(
        "CAND_X",
        "SERVED_X",
        [read(date(2026, 11, 18), date(2026, 11, 18))],
        served_source="imf",
        candidate_source="eurostat",
        country="DE",
        served_latest=OCT,
        candidate_latest=OCT,
    )
    assert flipped.verdict == "level" and flipped.recommendation == "replace"


# --- a period one side has not shown yet ---------------------------------------------------


def test_a_candidate_with_nothing_yet_is_later_than_the_day_it_was_last_loaded():
    r = read(date(2026, 11, 18), None, candidate_loaded=date(2026, 11, 22))
    assert r.bound and (r.served_lag, r.candidate_lag) == (18, 23)  # 22 days after, so at least 23
    assert judged(r).verdict == "served earlier" and judged(r).bounded


def test_a_served_series_with_nothing_yet_is_later_than_the_day_it_was_last_loaded():
    r = read(None, date(2026, 11, 12), served_loaded=date(2026, 11, 20))
    assert r.bound and r.served_lag > r.candidate_lag
    assert judged(r).recommendation == "replace"


def test_a_period_neither_side_could_have_shown_yet_is_not_counted():
    # served first read after the candidate was last loaded: the candidate could not have had it
    assert read(date(2026, 11, 25), None, candidate_loaded=date(2026, 11, 20)) is None


def test_nothing_is_decided_before_a_period_is_published_after_staging():
    m = judged()
    assert MIN_RELEASES == 1 and m.verdict == "insufficient" and m.recommendation == "insufficient"


# --- from the database -------------------------------------------------------------------


class FakeImf:
    def __init__(self, last):
        self.last = last

    def series(self, flow, key, start):
        end = self.last.year * 12 + self.last.month - 1
        periods = [date((end - i) // 12, (end - i) % 12 + 1, 1) for i in reversed(range(30))]
        from types import SimpleNamespace

        return SimpleNamespace(observations=[(p, 2.0 + i / 10) for i, p in enumerate(periods)])


def _serve_hicp_de(session, october_read):
    """ESTAT_HICP_DE with September already known and October first read on `october_read`."""
    months = [date(2024 + (m // 12), m % 12 + 1, 1) for m in range(34)]
    MacroStore(session).replace_series(
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
        [
            Vintage(p, october_read if p == OCT else p + timedelta(days=50), OPEN_END, 2.9)
            for p in months
            if p <= OCT
        ],
    )
    session.commit()


def test_the_measurement_reads_the_stored_sightings_and_first_releases(db_session):
    _serve_hicp_de(db_session, date(2026, 11, 18))
    start = date(2026, 11, 20)
    ingest({"imf": FakeImf(date(2026, 9, 1))}, db_session, [DE], today=start)  # Sep, bootstrap
    loaded = {"ESTAT_HICP_DE": date(2026, 11, 20), DE.id: date(2026, 11, 20)}

    [waiting] = measure_all(db_session, [DE], date(2026, 11, 20), loaded)
    assert waiting.verdict == "served earlier" and waiting.bounded  # October is not at the IMF yet
    assert (waiting.served_median, waiting.candidate_median) == (18, 21)

    later = date(2026, 11, 27)  # the IMF publishes October
    ingest({"imf": FakeImf(OCT)}, db_session, [DE], today=later)
    loaded[DE.id] = later
    [seen] = measure_all(db_session, [DE], later, loaded)
    assert (seen.served_median, seen.candidate_median) == (18, 27) and not seen.bounded
    assert seen.recommendation == "confirm"
