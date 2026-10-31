from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel


class DataFreshness(ApiModel):
    status: Literal["ok", "overdue", "discontinued", "review"]
    usable: bool = Field(
        description="False when overdue, discontinued or awaiting review: not current data"
    )
    next_due: date | None = Field(description="When the next release is expected")
    typical_lag_days: int = Field(description="Usual days from a period to its first release")
    days_overdue: int
    reason: str


class DataTimeliness(ApiModel):
    weight: float = Field(
        description="0-1 weight for scorecards: halves every 60 days between the end of a "
        "period and the day QuFin can read it; 0 when not usable"
    )
    source_lag_days: int = Field(description="Usual days from a period to the source's release")
    fred_delay_days: int = Field(description="Days FRED publishes after the source (licensing)")
    days_after_period_end: int
    latest_source_release: date | None = Field(
        description="When the source first published the latest period"
    )
    latest_fred_release: date | None = Field(
        description="When FRED shows the latest period (later by any declared delay)"
    )
    delay_note: str | None = Field(description="Why FRED publishes later than the source")
