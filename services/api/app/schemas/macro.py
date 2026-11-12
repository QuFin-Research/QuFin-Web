from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin
from app.schemas.freshness import DataFreshness, DataTimeliness
from app.schemas.market import ScoreDimension


class MacroSeries(ApiModel):
    id: str
    name: str = Field(description="Human-readable name shown to users, shared across countries")
    explanation: str = Field(description="One plain sentence on what the indicator measures")
    concept: str = Field(description="Concept key matching the same indicator across countries")
    acronym: str | None = Field(
        description="The indicator's global acronym, e.g. CPI, whatever the country calls its own"
    )
    source: str
    title: str = Field(description="The source's official title (for the tooltip)")
    units: str
    frequency: str
    seasonal_adjustment: str
    country: str
    dimension: ScoreDimension | Literal["external", "fiscal", "energy", "markets"] = Field(
        description='Scorecard pillar; "external" and "fiscal" are shown and scored once the '
        'scorecard has eight pillars; "energy" is oil supply and demand and "markets" are '
        "reference prices, never scored"
    )
    cycle: Literal["leading", "coincident", "lagging"] | None = Field(
        description="When the series tends to turn relative to the business cycle"
    )
    last_updated: datetime | None = Field(description="When the source last revised the series")
    unit_kind: str | None = Field(
        description="amount_currency, count, index, rate_percent, ratio, price_per_unit or other "
        "(rule 23: only series with the same kind, currency and unit share one scale)"
    )
    currency: str | None = Field(description="ISO currency of amounts and prices; null if none")
    source_name: str | None = Field(description="Who produces the data, e.g. the BLS")
    release_name: str | None = Field(description="The release the series is published in")
    canonical_code: str | None = Field(
        default=None,
        description="ISO3.PILLAR.INDICATOR.FREQ.ADJUSTMENT, unique across every series",
    )
    pillar: str | None = Field(
        default=None,
        description="Macro pillar: GROWTH, INFLATION, LABOR, MONETARY, SURVEYS, CONSUMPTION, "
        "TRADE or FISCAL; ENERGY and MARKETS are reference classes, never scored",
    )
    country_iso3: str | None = Field(default=None, description="ISO 3166 alpha-3 of the country")


class SeriesChange(ApiModel):
    horizon: str = Field(description='"1m", "3m", "1y"; "q/q" and "y/y" for quarterly series')
    value: float
    unit: str = Field(description='"%", "% ann." (annualised) or "pt" (in the series\' units)')


class MacroSeriesSummary(MacroSeries):
    ingested_at: datetime
    first_period: date | None
    last_period: date | None
    vintage_rows: int
    change_kind: Literal["pct", "diff"] = Field(
        description="pct: percent change (quantities, price indexes); diff: change in the "
        "series' own units (rates, spreads, indexes that can be zero or negative)"
    )
    published_as_change: bool = Field(
        description="The source already publishes it as a change or growth rate"
    )
    changes: list[SeriesChange] = Field(
        description="Latest moves, each within one vintage; daily and weekly series as "
        "28-day averages"
    )
    freshness: DataFreshness
    timeliness: DataTimeliness


class MacroObservation(ApiModel):
    period: date
    value: float | None
    realtime_start: date = Field(description="When this value was first published")


class MacroSeriesData(ApiModel):
    series: MacroSeries
    freshness: DataFreshness = Field(description="Release status of the series today")
    changes: list[SeriesChange] = Field(description="Latest moves as published on asOf")
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
