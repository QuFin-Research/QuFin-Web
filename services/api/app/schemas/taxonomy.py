from datetime import date, datetime, time
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin


class Country(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    iso3: str
    iso2: str
    name: str
    currency: str
    central_bank: str
    g7: bool
    g20: bool
    gcc: bool
    em: bool = Field(description="Emerging market (IMF World Economic Outlook grouping)")
    series_count: int = Field(description="Series stored for this country")
    pillars: dict[str, int] = Field(description="Stored series per pillar")


class Indicator(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    concept: str = Field(description="Concept key shared by every country")
    name: str
    explanation: str
    acronym: str | None
    pillar: str
    series_count: int
    countries: list[str] = Field(description="ISO3 codes of the countries that have it")
    same_scale: bool = Field(
        description="False when the countries' stored values are not on one scale (rule 23)"
    )
    scale_note: str | None = Field(description="Why the stored scales differ, when they do")
    compared_as: str | None = Field(
        description="The basis countries are compared on where the stored scales differ"
    )


class PitObservation(ApiModel):
    period: date
    value: float | None
    vintage_date: date = Field(description="The day this value was first published or recorded")


class PitSeries(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    canonical_code: str
    series_id: str = Field(description="The source's own ticker")
    title: str
    units: str
    scale: float = Field(description="Multiplier of the units text (millions = 1e6)")
    frequency: str
    pillar: str
    as_of: datetime | None = Field(description="The moment asked for; null means the latest view")
    known_through: date | None = Field(
        description="Vintages dated up to and including this day were visible; null is the latest"
    )
    observations: list[PitObservation]


PillarStatus = Literal["scored", "not_scored_yet", "no_usable_data"]


class PillarScore(ApiModel):
    pillar: str
    status: PillarStatus
    score: float | None = Field(description="-3 to +3; null unless scored")
    confidence: float = Field(description="0 to 1, reported separately from the score")
    indicators: int = Field(description="Indicators that went into the score")


class PillarScores(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    country_iso3: str
    as_of: datetime
    known_through: date
    pillars: list[PillarScore]
    overall: float | None
    overall_confidence: float
    note: str


class EconomicEvent(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    canonical_code: str
    series_id: str
    period: date
    release_date: date
    release_time_utc: time | None = Field(description="Empty until the release time is recorded")
    status: Literal["released", "scheduled"]
    previous_value: float | None
    consensus_estimate: float | None = Field(
        description="Empty until a licensed consensus feed supplies it"
    )
    consensus_source: str | None
    actual_value: float | None = Field(description="The first print, as published at the release")
    surprise_score: float | None = Field(
        description="Standardised actual minus consensus; empty without consensus and history"
    )


class ComparisonPoint(ApiModel):
    period: date
    value: float


class ComparisonRow(ApiModel):
    iso3: str
    country: str
    series_id: str = Field(description="The source's own ticker")
    canonical_code: str | None
    publisher: str | None
    source_name: str | None
    period: date = Field(description="The latest period, on the comparison basis")
    value: float = Field(description="The latest value on the comparison basis")
    change_3m: float | None = Field(description="Points against three months earlier")
    change_12m: float | None = Field(description="Points against twelve months earlier")
    converted: bool = Field(
        description="True when the stored series is not on the comparison basis and was converted"
        " (the US price index becomes its year-on-year change)"
    )
    stored_as: str = Field(description="The units the series is stored in, as the source states")
    usable: bool = Field(description="False when the series is overdue; it is shown, not ranked")
    status_note: str = Field(description="Release status in words")
    history: list[ComparisonPoint] = Field(description="The last 36 months on the same basis")


class MissingCountry(ApiModel):
    iso3: str
    name: str


class Comparison(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    concept: str
    name: str
    explanation: str
    basis: str = Field(description="What the compared number is, e.g. Year-on-year change")
    unit: str
    method: str = Field(description="How each country's stored series was brought to the basis")
    higher_is: str
    rows: list[ComparisonRow] = Field(description="Ranked, highest value first; unusable last")
    missing: list[MissingCountry] = Field(
        description="Countries in the taxonomy with no series yet"
    )
