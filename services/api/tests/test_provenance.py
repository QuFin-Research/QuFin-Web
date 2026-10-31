"""No number reaches a user without its origin (rule in services/api/CLAUDE.md).

Every data endpoint's response says where its numbers come from: a `data` field ("live" or
"sample") or, for live sources checked against their release schedule, `freshness`. Adding an
endpoint without either fails here. Do not add exemptions for data endpoints.
"""

import types
import typing

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.main import create_app
from tests.test_backtests_api import rule_body, strategy_body

# Identity endpoints carry no market or economic numbers.
NO_DATA_PREFIXES = ("/v1/auth/",)


def _models(annotation) -> list[type[BaseModel]]:
    """The response model classes behind list[...], unions and Annotated[...]."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _models(typing.get_args(annotation)[0])
    if origin in (list, typing.Union, types.UnionType):
        return [m for arg in typing.get_args(annotation) for m in _models(arg)]
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    return []


def _api_routes(routes):
    """Every APIRoute, including those inside included routers."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif (nested := getattr(route, "original_router", None)) is not None:
            yield from _api_routes(nested.routes)


def test_every_data_endpoint_declares_where_its_numbers_come_from():
    app = create_app()
    checked = 0
    for route in _api_routes(app.routes):
        if route.response_model is None:
            continue
        if route.path.startswith(NO_DATA_PREFIXES):
            continue
        for model in _models(route.response_model):
            assert {"data", "freshness"} & set(model.model_fields), (
                f"{route.path} returns {model.__name__} without `data` or `freshness`"
            )
            checked += 1
    assert checked >= 10  # the check must actually cover the data endpoints


def test_sample_data_is_labelled_on_every_market_endpoint(client, user_client):
    assets = client.get("/v1/assets").json()
    assert {a["data"] for a in assets} == {"sample"}
    assert client.get("/v1/assets/XAUUSD").json()["data"] == "sample"
    for body in (strategy_body(), rule_body()):
        run = user_client.post("/v1/backtests", json=body)
        assert run.status_code == 200, run.text
        assert run.json()["data"] == "sample"
    # Without macro data the scorecard falls back to sample scores, labelled as such.
    assert {c["data"] for c in client.get("/v1/scorecards/countries").json()} == {"sample"}
