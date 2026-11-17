"""Admin and data-scientist views: coverage, scorecard freshness and data refresh runs."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ORIGIN_DESCRIPTION, ApiModel, DataOrigin

JobStatus = Literal["running", "succeeded", "failed", "interrupted"]
StepStatus = Literal["pending", "running", "ok", "overdue", "failed", "skipped"]
ScorecardState = Literal["updated", "partial", "stale"]


class IndicatorGap(ApiModel):
    concept: str
    indicator: str
    have: int
    unusable: int  # stored but overdue, or declared and not loaded
    gap: int


class CountryGap(ApiModel):
    iso3: str
    country: str
    have: int
    unusable: int
    gap: int


class CoverageHeadline(ApiModel):
    """The few numbers every admin and data scientist sees at sign-in."""

    countries: int
    countries_with_gaps: int
    applicable: int  # cells of the indicators that can exist for every country
    have: int
    unusable: int
    gap: int
    coverage_pct: float


class CoverageSummary(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    generated_at: datetime
    headline: CoverageHeadline
    global_indicators: int
    by_indicator: list[IndicatorGap]
    by_country: list[CountryGap]
    overdue_series: list[str]


class JobStep(ApiModel):
    command: str
    source: str
    series: int
    status: StepStatus
    detail: str = ""


class JobRun(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    id: str
    job: str
    status: JobStatus
    requested_by: str
    started_at: datetime
    finished_at: datetime | None
    steps: list[JobStep]
    error: str | None


class ScorecardStatus(ApiModel):
    """Whether the scorecard is being kept up to date by the backend."""

    state: ScorecardState
    reason: str
    latest_period: date | None
    scored_series: int
    usable_series: int
    overdue_series: list[str]
    data_loaded_at: datetime | None  # the newest ingest of any series


class AdminStatus(ApiModel):
    data: DataOrigin = Field(default="live", description=ORIGIN_DESCRIPTION)
    scorecard: ScorecardStatus
    coverage: CoverageHeadline
    last_run: JobRun | None
    running: bool
    next_refresh_allowed_at: datetime | None


class RefreshRequest(ApiModel):
    """Empty on purpose: a JSON body is required, so a cross-site form cannot start a run."""
