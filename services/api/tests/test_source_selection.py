"""Rule 38: the source of a pair is chosen on objective measures, and the same input always gives
the same choice."""

from datetime import date
from itertools import permutations

import pytest

from app.domain.source_selection import Candidate, choose

OCT, SEP = date(2026, 10, 1), date(2026, 9, 1)


def c(source, producer="global", lag=None, freq="monthly", period=None, eligible=True):
    return Candidate(source, eligible, freq, producer, lag, period)


def test_an_ineligible_source_is_never_chosen_however_early_it_is():
    best = choose([c("fast", lag=1, eligible=False), c("slow", lag=40)])
    assert best.source == "slow"
    assert choose([c("a", eligible=False), c("b", eligible=False)]) is None
    assert choose([]) is None


def test_the_earliest_source_wins_even_over_a_more_native_one():
    best = choose([c("eurostat", "bloc", lag=30), c("imf", "global", lag=10)])
    assert best.source == "imf"


def test_equally_early_sources_are_separated_by_frequency():
    best = choose([c("a", lag=20, freq="monthly"), c("b", lag=20, freq="weekly")])
    assert best.source == "b"


def test_a_tie_goes_to_the_most_native_source():
    european = [c("imf", "global", lag=20), c("eurostat", "bloc", lag=20)]
    assert choose(european).source == "eurostat"  # Eurostat rather than the IMF
    american = [c("worldbank", "global", lag=20), c("fred", "bloc", lag=20), c("imf", lag=20)]
    assert choose(american).source == "fred"
    origin = [c("eurostat", "bloc", lag=20), c("destatis", "original", lag=20)]
    assert choose(origin).source == "destatis"  # the original producer first


def test_equally_native_sources_are_ranked_by_freshness_then_by_source_code():
    fresher = [c("oecd", period=SEP, lag=20), c("imf", period=OCT, lag=20)]
    assert choose(fresher).source == "imf"
    same = [c("oecd", period=OCT, lag=20), c("bis", period=OCT, lag=20)]
    assert choose(same).source == "bis"  # source code ascending


@pytest.mark.parametrize(
    "candidates",
    [
        [c("imf", lag=20, period=OCT), c("oecd", lag=20, period=OCT), c("worldbank", lag=20)],
        [c("imf"), c("eurostat", "bloc"), c("bis", period=OCT)],
    ],
)
def test_the_choice_never_depends_on_the_order_the_candidates_are_loaded(candidates):
    winners = {choose(order).source for order in permutations(candidates)}
    assert len(winners) == 1


def test_a_new_pair_is_served_from_the_most_recent_period_then_frequency_then_nativeness():
    """No lag is measured yet (rule 38, New pairs): the probe decides."""
    new = [c("imf", period=SEP), c("eurostat", "bloc", period=OCT)]
    assert choose(new).source == "eurostat"
    level = [c("imf", period=OCT), c("eurostat", "bloc", period=OCT)]
    assert choose(level).source == "eurostat"  # the same period: the native source
    faster = [c("a", period=OCT, freq="monthly"), c("b", "global", period=OCT, freq="daily")]
    assert choose(faster).source == "b"


def test_the_eurostat_decisions_of_19_nov_2026_follow_from_the_probe():
    """Germany: Eurostat held October, the IMF September. Belgium: both held October, a tie."""
    germany = [c("imf", period=SEP), c("eurostat", "bloc", period=OCT)]
    belgium = [c("imf", period=OCT), c("eurostat", "bloc", period=OCT)]
    assert choose(germany).source == choose(belgium).source == "eurostat"


def test_an_unknown_frequency_is_refused_not_guessed():
    with pytest.raises(ValueError, match="unknown frequency"):
        choose([c("a", freq="fortnightly")])


# --- Bloc aggregator first (rule 38, v3.5) -----------------------------------------------------


def test_bloc_aggregator_of_names_eurostat_for_its_economies_only():
    from app.domain.source_selection import bloc_aggregator_of

    for country in ("DE", "EA", "CH", "AL", "XK", "TR"):
        assert bloc_aggregator_of(country) == "eurostat"
    for country in ("US", "JP", "GB", "CA"):
        assert bloc_aggregator_of(country) is None


def test_an_eligible_eurostat_candidate_wins_however_early_another_is():
    field = [c("destatis", "original", lag=1), c("imf", lag=2), c("eurostat", "bloc", lag=40)]
    assert choose(field, bloc_aggregator="eurostat").source == "eurostat"
    assert choose(field).source == "destatis"  # without the rule the measures decide


def test_every_candidate_is_back_when_eurostat_is_ineligible_or_absent():
    ineligible = [c("imf", lag=5), c("eurostat", "bloc", lag=1, eligible=False)]
    assert choose(ineligible, bloc_aggregator="eurostat").source == "imf"
    assert choose([c("imf", lag=5), c("oecd", lag=9)], bloc_aggregator="eurostat").source == "imf"
