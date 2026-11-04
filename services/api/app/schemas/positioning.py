from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.freshness import DataFreshness


class PositioningPoint(ApiModel):
    report_date: date = Field(description="Positions as of this Tuesday")
    release_date: date = Field(description="When the CFTC made the report public")
    open_interest: int
    net: int = Field(description="The speculative group's net contracts, in the asset's direction")
    net_pct_oi: float = Field(description="Net position as a % of open interest")
    cot_index: float | None = Field(
        description="Net position within its 3-year range: 0 most bearish, 100 most bullish"
    )
    asset_manager_net: int | None = Field(
        description="Asset managers' net contracts, in the asset's direction (financial only)"
    )


class PositioningSnapshot(ApiModel):
    symbol: str
    contract_code: str
    market_name: str
    report: Literal["legacy", "tff"] = Field(
        description='CFTC report: "tff" (Traders in Financial Futures) or "legacy" (commodities)'
    )
    group: str = Field(description="Whose net position the metrics follow")
    latest: PositioningPoint
    weekly_change: int | None = Field(description="Change in net contracts from the prior week")
    caveat: str | None = Field(description="Limits of this contract as a view of the market")
    freshness: DataFreshness = Field(description="Release status as of the requested date")


class PositioningHistory(ApiModel):
    symbol: str
    contract_code: str
    market_name: str
    report: Literal["legacy", "tff"] = Field(
        description='CFTC report: "tff" (Traders in Financial Futures) or "legacy" (commodities)'
    )
    group: str = Field(description="Whose net position the metrics follow")
    as_of: date | None
    caveat: str | None = Field(description="Limits of this contract as a view of the market")
    freshness: DataFreshness = Field(description="Release status as of the requested date")
    points: list[PositioningPoint]
