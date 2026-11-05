from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.auth import AppSettings, DbSession
from app.core.clock import Today
from app.data.repository import MarketRepository, get_market_repository
from app.domain import methodology
from app.domain.market import asset_detail, list_snapshots
from app.jobs.scorecard import to_country_score, us_scorecard
from app.schemas.market import (
    AssetDetail,
    AssetSnapshot,
    CountryScore,
    Methodology,
    MethodologyDetails,
)

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
def get_country_scores(
    repo: Repo,
    session: DbSession,
    today: Today,
    settings: AppSettings,
    as_of: Annotated[
        date | None,
        Query(alias="asOf", description="Score with the data as published on this date"),
    ] = None,
) -> list[CountryScore]:
    """Macro scorecards by country, strongest overall first.

    Live scorecards come from the point-in-time macro store (US today); each pillar is a
    rescaled weighted average of its usable indicators, with confidence reported separately.
    Without macro data the sample scorecards are returned, marked `data: "sample"`; live and
    sample economies are never mixed in one ranking.
    """
    shown = settings.scorecard_mechanism == "show"
    live = us_scorecard(session, as_of or today)
    cards = repo.get_country_scores() if live is None else [to_country_score(live)]
    return [_disclose(card, shown) for card in cards]


def _disclose(card: CountryScore, shown: bool) -> CountryScore:
    """QuFin's choice (rule 20): weights and sub-scores only when the mechanism is shown."""
    if shown:
        return card.model_copy(update={"mechanism": "shown"})
    return card.model_copy(update={"mechanism": "hidden", "indicators": []})


@router.get("/scorecards/methodology", response_model=Methodology)
def get_methodology(settings: AppSettings) -> Methodology:
    """What QuFin tells users about the scorecard: always a summary, the full mechanism only
    when QuFin has set `scorecard_mechanism` to show."""
    if settings.scorecard_mechanism != "show":
        return Methodology(mechanism="hidden", summary=methodology.SUMMARY)
    return Methodology(
        mechanism="shown",
        summary=methodology.SUMMARY,
        details=MethodologyDetails(**methodology.mechanism()),
    )
