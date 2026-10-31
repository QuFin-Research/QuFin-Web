from datetime import date, datetime

from pydantic import Field

from app.schemas.base import ApiModel
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
    last_updated: datetime | None = Field(description="When the source last revised the series")


class MacroSeriesSummary(MacroSeries):
    ingested_at: datetime
    first_period: date | None
    last_period: date | None
    vintage_rows: int


class MacroObservation(ApiModel):
    period: date
    value: float | None
    realtime_start: date = Field(description="When this value was first published")


class MacroSeriesData(ApiModel):
    series: MacroSeries
    as_of: date | None = Field(description="Real-time date of this view; null means latest")
    observations: list[MacroObservation]


class MacroRevision(ApiModel):
    realtime_start: date
    realtime_end: date | None = Field(description="Null while this is still the current value")
    value: float | None


class MacroRevisionHistory(ApiModel):
    series: MacroSeries
    period: date
    revisions: list[MacroRevision] = Field(description="First release first")
