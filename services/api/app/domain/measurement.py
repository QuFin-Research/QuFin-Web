"""The lag of a source, measured on the same observation (rule 38, "Earliest").

"Earliest" is the time from the end of a period to the moment QuFin can first read it, compared
between the series that serves a pair and a staged candidate for it, over at least one release
cycle.
A period counts only if it was published after QuFin started looking at the candidate: periods
present at the first load say nothing about timing (`candidate_sightings.bootstrap`).

A period one source has shown and the other has not yet is not dropped. If the served series was
first read on or before the day the candidate was last loaded, and the candidate had nothing then,
the candidate is later: its lag is at least the days since the period ended. The same holds
the other way round. That way a source slow to publish loses by being slow, not by being silent.

This module only judges. It reads no database and records no decision (slice 3).
"""

import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from app.domain.source_selection import Candidate, Producer, bloc_aggregator_of, choose

# Rule 38: "over at least one release cycle".
MIN_RELEASES = 1

ORIGINAL_PRODUCERS = frozenset({"bls", "eia", "treasury", "ons", "bcb", "singstat", "cftc"})

Winner = Literal["served", "candidate", "level"]


def producer_of(source: str, country: str) -> Producer:
    """How native a source is for an economy (Part 0): the original producer, the aggregator of its
    own bloc (Eurostat for Europe, FRED for the United States), or a global aggregator."""
    if source in ORIGINAL_PRODUCERS:
        return "original"
    if source == "eurostat" or (source == "fred" and country == "US"):
        return "bloc"
    return "global"


def period_end(period: date, months: int = 1) -> date:
    """The last day of the period that starts on `period` (a month by default)."""
    year, month = divmod(period.month - 1 + months, 12)
    return date(period.year + year, month + 1, 1) - timedelta(days=1)


def lag_days(period: date, first_read: date, months: int = 1) -> int:
    """Days from the end of the period to the day it was first read."""
    return (first_read - period_end(period, months)).days


@dataclass(frozen=True)
class PeriodRead:
    """One period read from both sides: the lag of each, or the bound where one is still missing."""

    period: date
    served_lag: int
    candidate_lag: int
    bound: bool  # one lag is a lower bound, because that source had not shown the period yet

    @property
    def winner(self) -> Winner:
        if self.served_lag < self.candidate_lag:
            return "served"
        if self.candidate_lag < self.served_lag:
            return "candidate"
        return "level"


@dataclass(frozen=True)
class Measurement:
    candidate_id: str
    serves: str
    periods: list[PeriodRead] = field(default_factory=list)
    served_median: int | None = None
    candidate_median: int | None = None
    served_wins: int = 0
    candidate_wins: int = 0
    level: int = 0
    bounded: bool = False  # a lag is a lower bound: one side had not shown a period yet
    verdict: str = "insufficient"  # served earlier, candidate earlier, level, insufficient
    recommendation: str = "insufficient"  # confirm, replace, insufficient


def read_period(
    period: date,
    *,
    served_read: date | None,
    candidate_read: date | None,
    served_loaded: date,
    candidate_loaded: date,
    months: int = 1,
) -> PeriodRead | None:
    """Both lags of one period, a bound for the side that has not shown it, or None if unknown."""
    if served_read is not None and candidate_read is not None:
        return PeriodRead(
            period,
            lag_days(period, served_read, months),
            lag_days(period, candidate_read, months),
            False,
        )
    if served_read is not None and served_read <= candidate_loaded:
        # the candidate was loaded since and held nothing: it is later than the day it was last read
        return PeriodRead(
            period,
            lag_days(period, served_read, months),
            lag_days(period, candidate_loaded, months) + 1,
            True,
        )
    if candidate_read is not None and candidate_read <= served_loaded:
        return PeriodRead(
            period,
            lag_days(period, served_loaded, months) + 1,
            lag_days(period, candidate_read, months),
            True,
        )
    return None


def measure(
    candidate_id: str,
    serves: str,
    reads: Iterable[PeriodRead],
    *,
    served_source: str,
    candidate_source: str,
    country: str,
    served_latest: date | None,
    candidate_latest: date | None,
    frequency: str = "monthly",
) -> Measurement:
    """Judge the periods and say what rule 38 would do: confirm the series that serves the pair,
    replace it with the candidate, or wait for more periods."""
    periods = sorted(reads, key=lambda r: r.period)
    if len(periods) < MIN_RELEASES:
        return Measurement(candidate_id, serves, periods)
    served_median = round(statistics.median(r.served_lag for r in periods))
    candidate_median = round(statistics.median(r.candidate_lag for r in periods))
    wins = [r.winner for r in periods]
    served_wins, candidate_wins = wins.count("served"), wins.count("candidate")
    if served_wins > candidate_wins:
        verdict = "served earlier"
    elif candidate_wins > served_wins:
        verdict = "candidate earlier"
    else:
        verdict = "level"
    chosen = choose(
        [
            Candidate(
                served_source,
                True,
                frequency,
                producer_of(served_source, country),
                served_median,
                served_latest,
            ),
            Candidate(
                candidate_source,
                True,
                frequency,
                producer_of(candidate_source, country),
                candidate_median,
                candidate_latest,
            ),
        ],
        bloc_aggregator=bloc_aggregator_of(country),
    )
    recommendation = "confirm" if chosen and chosen.source == served_source else "replace"
    return Measurement(
        candidate_id,
        serves,
        periods,
        served_median,
        candidate_median,
        served_wins,
        candidate_wins,
        wins.count("level"),
        any(r.bound for r in periods),
        verdict,
        recommendation,
    )
