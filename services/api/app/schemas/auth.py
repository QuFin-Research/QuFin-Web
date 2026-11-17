from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, Field

from app.schemas.base import ApiModel


def _normalise_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


Email = Annotated[
    str,
    BeforeValidator(_normalise_email),
    Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("Password cannot be only spaces")
    return value


class SignUp(ApiModel):
    email: Email
    # ASVS 2.1: at least 12 characters, long passphrases allowed, no composition rules.
    password: Annotated[str, Field(min_length=12, max_length=128), AfterValidator(_not_blank)]


class SignIn(ApiModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


Role = Literal["admin", "data_scientist", "user"]


class User(ApiModel):
    id: str
    email: str
    created_at: datetime
    # Decided by the server from its settings on every request, never stored or sent by a client.
    role: Role = "user"
