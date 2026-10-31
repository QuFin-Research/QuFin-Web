from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.auth import DbSession
from app.schemas.macro import (
    MacroObservation,
    MacroRevision,
    MacroRevisionHistory,
    MacroSeries,
    MacroSeriesData,
    MacroSeriesSummary,
)
from app.stores.macro import OPEN_END, MacroStore, SeriesMeta

router = APIRouter(prefix="/v1/macro", tags=["macro"])

SeriesId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_.]{1,64}$")]


def get_store(session: DbSession) -> MacroStore:
    return MacroStore(session)


Store = Annotated[MacroStore, Depends(get_store)]


def _series(meta: SeriesMeta) -> MacroSeries:
    return MacroSeries.model_validate(meta, from_attributes=True)


def _require(store: MacroStore, series_id: str) -> SeriesMeta:
    meta = store.get_series(series_id.upper())
    if meta is None:
        raise HTTPException(status_code=404, detail="Series not ingested")
    return meta


@router.get("/series", response_model=list[MacroSeriesSummary])
def list_series(store: Store) -> list[MacroSeriesSummary]:
    """Macro series in the point-in-time store, with their coverage."""
    return [
        MacroSeriesSummary(
            **_series(s.meta).model_dump(),
            ingested_at=s.ingested_at,
            first_period=s.first_period,
            last_period=s.last_period,
            vintage_rows=s.vintage_rows,
        )
        for s in store.list_series()
    ]


@router.get("/series/{series_id}", response_model=MacroSeriesData)
def get_series(
    store: Store,
    series_id: SeriesId,
    as_of: Annotated[
        date | None,
        Query(alias="asOf", description="Show the data as published on this date"),
    ] = None,
    start: Annotated[date | None, Query(description="First period")] = None,
    end: Annotated[date | None, Query(description="Last period")] = None,
) -> MacroSeriesData:
    """The series as it was known on `asOf` (point in time), or the latest values.

    Use `asOf` in backtests and scorecards: it only returns what had been published by that
    date, so later revisions cannot leak into past decisions.
    """
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")
    meta = _require(store, series_id)
    vintages = store.as_of(meta.id, as_of, start, end)
    return MacroSeriesData(
        series=_series(meta),
        as_of=as_of,
        observations=[
            MacroObservation(period=v.period, value=v.value, realtime_start=v.realtime_start)
            for v in vintages
        ],
    )


@router.get("/series/{series_id}/revisions", response_model=MacroRevisionHistory)
def get_revisions(
    store: Store,
    series_id: SeriesId,
    period: Annotated[date, Query(description="The observation period, e.g. 2026-09-01")],
) -> MacroRevisionHistory:
    """Every published value of one period, from first release to the latest revision."""
    meta = _require(store, series_id)
    revisions = store.revisions(meta.id, period)
    if not revisions:
        raise HTTPException(status_code=404, detail="No observation for that period")
    return MacroRevisionHistory(
        series=_series(meta),
        period=period,
        revisions=[
            MacroRevision(
                realtime_start=v.realtime_start,
                realtime_end=None if v.realtime_end == OPEN_END else v.realtime_end,
                value=v.value,
            )
            for v in revisions
        ],
    )
