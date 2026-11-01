from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin
from app.schemas.freshness import DataFreshness, DataTimeliness
from app.schemas.market import ScoreDimension


class MacroSeries(ApiModel):
    id: str
    source: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    country: str
    dimension: ScoreDimension
    cycle: Literal["leading", "coincident", "lagging"] | None = Field(
        description="When the series tends to turn relative to the business cycle"
    )
    last_updated: datetime | None = Field(description="When the source last revised the series")
    source_name: str | None = Field(description="Who produces the data, e.g. the BLS")
    release_name: str | None = Field(description="The release the series is published in")


class MacroSeriesSummary(MacroSeries):
    ingested_at: datetime
    first_period: date | None
    last_period: date | None
    vintage_rows: int
    freshness: DataFreshness
    timeliness: DataTimeliness


class MacroObservation(ApiModel):
    period: date
    value: float | None
    realtime_start: date = Field(description="When this value was first published")


class MacroSeriesData(ApiModel):
    series: MacroSeries
    freshness: DataFreshness = Field(description="Release status of the series today")
    timeliness: DataTimeliness
    as_of: date | None = Field(description="Real-time date of this view; null means latest")
    observations: list[MacroObservation]


class MacroRevision(ApiModel):
    realtime_start: date
    realtime_end: date | None = Field(description="Null while this is still the current value")
    value: float | None


class MacroRevisionHistory(ApiModel):
    data: DataOrigin = Field(description=ORIGIN_DESCRIPTION)
    series: MacroSeries
    period: date
    revisions: list[MacroRevision] = Field(description="First release first")
