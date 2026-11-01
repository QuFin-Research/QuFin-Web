from datetime import date

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.freshness import DataFreshness


class PositioningPoint(ApiModel):
    report_date: date = Field(description="Positions as of this Tuesday")
    release_date: date = Field(description="When the CFTC made the report public")
    open_interest: int
    net: int = Field(description="Large speculators' net contracts, in the asset's direction")
    net_pct_oi: float = Field(description="Net position as a % of open interest")
    cot_index: float | None = Field(
        description="Net position within its 3-year range: 0 most bearish, 100 most bullish"
    )


class PositioningSnapshot(ApiModel):
    symbol: str
    contract_code: str
    market_name: str
    latest: PositioningPoint
    weekly_change: int | None = Field(description="Change in net contracts from the prior week")
    caveat: str | None = Field(description="Limits of this contract as a view of the market")
    freshness: DataFreshness = Field(description="Release status as of the requested date")


class PositioningHistory(ApiModel):
    symbol: str
    contract_code: str
    market_name: str
    as_of: date | None
    caveat: str | None = Field(description="Limits of this contract as a view of the market")
    freshness: DataFreshness = Field(description="Release status as of the requested date")
    points: list[PositioningPoint]
