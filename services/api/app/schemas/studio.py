from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin

Metric = Literal["actual", "poc"]


class StudioPoint(ApiModel):
    period: date
    value: float


class StudioSeries(ApiModel):
    series_id: str
    canonical_code: str | None
    iso3: str
    country: str
    label: str = Field(description="Name and country, for a legend")
    concept: str | None
    native_frequency: str
    adjustment: Literal["SA", "NSA", "OTHER"] = Field(
        description="Seasonal adjustment as the source states it (Rule B)"
    )
    adjustment_text: str
    units: str = Field(description="Units as the source states them")
    display_unit: str = Field(description="The unit of `points`: the source's, %, or pp")
    aggregation: Literal["end", "mean", "sum"] | None = Field(
        description="How a faster series was collapsed to the display frequency; null if it was not"
    )
    metric_note: str | None = Field(description="How the change was taken, when metric is poc")
    axis: int = Field(description="Series sharing an axis share a unit; overlay charts use it")
    publisher: str | None
    last_vintage: date | None = Field(
        description="Date the latest published value of any period was released (Rule C)"
    )
    usable: bool
    status_note: str
    points: list[StudioPoint]


class StudioResult(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    mode: Literal["countries", "indicators"]
    name: str
    metric: Metric
    frequency: str = Field(description="The display frequency every series was put on")
    poc_name: str | None = Field(description="Week-over-Week, Month-over-Month, and so on")
    allowed_frequencies: list[str]
    restriction: str | None = Field(description="Why some frequencies are not available (Rule G)")
    notices: list[str] = Field(description="Anything the reader must know: mixed SA/NSA, scale")
    series: list[StudioSeries]


class StudioIndicator(ApiModel):
    concept: str
    name: str
    explanation: str
    countries: list[str] = Field(description="ISO3 codes with a stored series")


class StudioCatalogSeries(ApiModel):
    series_id: str
    canonical_code: str | None
    iso3: str
    concept: str | None
    name: str
    native_frequency: str
    adjustment: Literal["SA", "NSA", "OTHER"]
    units: str
    source: str
    publisher: str | None
    last_period: date | None
    last_updated: date | None = Field(description="When the source last updated the series")


class StudioCatalog(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    max_countries: int
    frequencies: list[str]
    indicators: list[StudioIndicator]
    series: list[StudioCatalogSeries]
