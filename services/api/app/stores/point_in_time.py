"""Point-in-time queries by canonical code (ADR 0007).

Observations carry the day they were first published or recorded (`realtime_start`), so a value
revised later is a new vintage and the old one is kept. These queries ask what was known at a
moment, never what is known now, which keeps backtests free of look-ahead.

A vintage is dated, not timed. A vintage dated D counts as known from the start of D+1 (UTC):
a timestamp during D could be before the release, and assuming it was after would let the future
in. This errs late, like every release date (rule 9).
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.taxonomy import (
    COUNTRY_BY_ISO3,
    PILLARS,
    SCORED_DIMENSION_PILLAR,
)
from app.schemas.taxonomy import PillarScore, PillarScores, PitObservation, PitSeries
from app.stores.macro import MacroSeriesRow, MacroStore, Vintage


class SeriesNotFoundError(LookupError):
    pass


class CountryNotFoundError(LookupError):
    pass


def known_through(as_of: datetime) -> date:
    """The last vintage date visible at `as_of`: the day before it (UTC)."""
    aware = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
    return aware.astimezone(UTC).date() - timedelta(days=1)


def _observation(v: Vintage) -> PitObservation:
    return PitObservation(period=v.period, value=v.value, vintage_date=v.realtime_start)


class PointInTime:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.store = MacroStore(session)

    def _row(self, code: str) -> MacroSeriesRow:
        row = self.session.scalars(
            select(MacroSeriesRow).where(MacroSeriesRow.canonical_code == code)
        ).first()
        if row is None:
            raise SeriesNotFoundError(code)
        return row

    def _series(
        self,
        row: MacroSeriesRow,
        as_of: datetime | None,
        start: date | None,
        end: date | None,
    ) -> PitSeries:
        cutoff = known_through(as_of) if as_of is not None else None
        vintages = self.store.as_of(row.id, cutoff, start, end)
        return PitSeries(
            canonical_code=row.canonical_code or "",
            series_id=row.id,
            title=row.title,
            units=row.units,
            scale=row.scale,
            frequency=row.frequency,
            pillar=row.pillar or "",
            as_of=as_of,
            known_through=cutoff,
            observations=[_observation(v) for v in vintages],
        )

    def get_latest_series(
        self, canonical_code: str, start_date: date | None = None, end_date: date | None = None
    ) -> PitSeries:
        """The most recent vintage of each observation date."""
        return self._series(self._row(canonical_code), None, start_date, end_date)

    def get_point_in_time_series(
        self,
        canonical_code: str,
        as_of_timestamp: datetime,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PitSeries:
        """The series exactly as it was known at `as_of_timestamp`: later releases and
        revisions are absent, and each period shows the value then current."""
        return self._series(self._row(canonical_code), as_of_timestamp, start_date, end_date)

    def compute_macro_pillar_scores(
        self, country_iso3: str, as_of_timestamp: datetime
    ) -> PillarScores:
        """Pillar scores as the scorecard would have shown them at `as_of_timestamp`.

        Only the United States has a live scorecard (ADR 0005); for any other country every
        pillar reads "not scored yet" rather than a made-up score (rule 8). The live scorecard
        scores five pillars; they are shown under their canonical names, and TRADE, CONSUMPTION
        and FISCAL stay unscored until the scorecard moves to eight pillars.
        """
        from app.jobs.scorecard import us_scorecard  # the scorecard job imports the stores

        if country_iso3 not in COUNTRY_BY_ISO3:
            raise CountryNotFoundError(country_iso3)
        cutoff = known_through(as_of_timestamp)
        card = us_scorecard(self.session, cutoff) if country_iso3 == "USA" else None
        scored = {
            SCORED_DIMENSION_PILLAR[dimension]: ps
            for dimension, ps in (card.scorecard.pillars.items() if card else ())
            if dimension in SCORED_DIMENSION_PILLAR
        }
        pillars = []
        for pillar in PILLARS:
            ps = scored.get(pillar)
            if ps is None:
                pillars.append(
                    PillarScore(
                        pillar=pillar,
                        status="not_scored_yet",
                        score=None,
                        confidence=0.0,
                        indicators=0,
                    )
                )
                continue
            used = sum(1 for i in ps.indicators if i.score is not None)
            pillars.append(
                PillarScore(
                    pillar=pillar,
                    status="scored" if ps.score is not None else "no_usable_data",
                    score=ps.score,
                    confidence=ps.confidence,
                    indicators=used,
                )
            )
        return PillarScores(
            country_iso3=country_iso3,
            as_of=as_of_timestamp,
            known_through=cutoff,
            pillars=pillars,
            overall=card.scorecard.overall if card else None,
            overall_confidence=card.scorecard.overall_confidence if card else 0.0,
            note=(
                "Scores are the live scorecard's five pillars under their canonical names; "
                "SURVEYS still carries financial-conditions indicators, and TRADE, CONSUMPTION "
                "and FISCAL are stored but not scored until the scorecard moves to eight pillars "
                "(ADR 0005). Only the United States is scored."
            ),
        )
