from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.auth import DbSession
from app.data.positioning_catalog import BY_SYMBOL, COT_CONTRACTS
from app.domain import positioning
from app.schemas.positioning import PositioningHistory, PositioningPoint, PositioningSnapshot
from app.stores.positioning import PositioningStore

router = APIRouter(prefix="/v1/positioning", tags=["positioning"])

AsOf = Annotated[
    date | None,
    Query(alias="asOf", description="Only reports released by this date (point in time)"),
]


def get_store(session: DbSession) -> PositioningStore:
    return PositioningStore(session)


Store = Annotated[PositioningStore, Depends(get_store)]


def _point(p: positioning.PositioningPoint) -> PositioningPoint:
    return PositioningPoint.model_validate(p, from_attributes=True)


@router.get("", response_model=list[PositioningSnapshot])
def list_positioning(store: Store, as_of: AsOf = None) -> list[PositioningSnapshot]:
    """Latest CFTC speculative positioning for every asset with ingested reports."""
    result = []
    for contract in COT_CONTRACTS:
        reports = store.history(contract.code, as_of)
        if not reports:
            continue
        points = positioning.series(contract, reports)
        result.append(
            PositioningSnapshot(
                symbol=contract.symbol,
                contract_code=contract.code,
                market_name=reports[-1].market_name,
                latest=_point(points[-1]),
                weekly_change=points[-1].net - points[-2].net if len(points) > 1 else None,
            )
        )
    return result


@router.get("/{symbol}", response_model=PositioningHistory)
def get_positioning(
    store: Store,
    symbol: Annotated[str, Path(pattern=r"^[A-Za-z0-9]{2,12}$")],
    as_of: AsOf = None,
    weeks: Annotated[int, Query(ge=1, le=1040, description="Most recent weeks to return")] = 156,
) -> PositioningHistory:
    """Weekly positioning history; the COT index of each week uses only data up to it."""
    contract = BY_SYMBOL.get(symbol.upper())
    if contract is None:
        raise HTTPException(status_code=404, detail="No CFTC contract for that symbol")
    reports = store.history(contract.code, as_of)
    if not reports:
        raise HTTPException(status_code=404, detail="No reports ingested for that symbol")
    points = positioning.series(contract, reports)[-weeks:]
    return PositioningHistory(
        symbol=contract.symbol,
        contract_code=contract.code,
        market_name=reports[-1].market_name,
        as_of=as_of,
        points=[_point(p) for p in points],
    )
