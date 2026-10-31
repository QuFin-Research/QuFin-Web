from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.data.repository import MarketRepository, get_market_repository
from app.domain.market import asset_detail, list_snapshots
from app.schemas.market import AssetDetail, AssetSnapshot, CountryScore

router = APIRouter(prefix="/v1", tags=["market"])

Repo = Annotated[MarketRepository, Depends(get_market_repository)]


@router.get("/assets", response_model=list[AssetSnapshot])
def get_assets(repo: Repo) -> list[AssetSnapshot]:
    """Latest snapshot (price, regime, signal, walk-forward hit rate) for every asset."""
    return list_snapshots(repo)


@router.get("/assets/{symbol}", response_model=AssetDetail)
def get_asset(
    repo: Repo,
    symbol: Annotated[str, Path(min_length=2, max_length=12, pattern=r"^[A-Za-z0-9]+$")],
) -> AssetDetail:
    """Full history of candles and signals for one asset, plus the latest signal's drivers."""
    detail = asset_detail(repo, symbol.upper())
    if detail is None:
        raise HTTPException(status_code=404, detail="Unknown symbol")
    return detail


@router.get("/scorecards/countries", response_model=list[CountryScore])
def get_country_scores(repo: Repo) -> list[CountryScore]:
    """Macro scorecards by country, strongest overall first."""
    return repo.get_country_scores()
