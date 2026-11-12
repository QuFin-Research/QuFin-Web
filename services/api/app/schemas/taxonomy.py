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
