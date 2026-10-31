from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for every API schema: snake_case in Python, camelCase on the wire
    (matching the TypeScript types in apps/web). Unknown fields are rejected."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


# Where the numbers in a response come from. "sample": generated for development by
# app/data/sample.py, not market data and not a trading signal. Every data endpoint states it
# (or carries `freshness` for live sources); tests/test_provenance.py enforces that.
DataOrigin = Literal["live", "sample"]
ORIGIN_DESCRIPTION = (
    "Where these numbers come from. 'sample' means generated for development: not market "
    "data and not a trading signal"
)
