from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy.orm import Session

from app.data.repository import MarketRepository, get_market_repository
from app.schemas.decisions import Decision, DecisionCreate
from app.stores.decisions import DecisionStore, get_session

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


def get_store(session: Annotated[Session, Depends(get_session)]) -> DecisionStore:
    return DecisionStore(session)


Store = Annotated[DecisionStore, Depends(get_store)]


@router.get("", response_model=list[Decision])
def list_decisions(store: Store) -> list[Decision]:
    """Logged decisions, newest first."""
    return store.list()


@router.post("", response_model=Decision, status_code=201)
def create_decision(
    data: DecisionCreate,
    store: Store,
    repo: Annotated[MarketRepository, Depends(get_market_repository)],
) -> Decision:
    if repo.get_asset(data.symbol) is None:
        raise HTTPException(status_code=422, detail="Unknown symbol")
    return store.add(data)


@router.delete("/{decision_id}", status_code=204)
def delete_decision(
    store: Store,
    decision_id: Annotated[str, Path(pattern=r"^[0-9a-fA-F-]{36}$")],
) -> Response:
    if not store.delete(decision_id):
        raise HTTPException(status_code=404, detail="Decision not found")
    return Response(status_code=204)
