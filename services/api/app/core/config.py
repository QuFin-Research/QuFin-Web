from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from QUFIN_* environment variables or a local .env.

    Nothing secret has a default: anything sensitive must come from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="QUFIN_", env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    database_url: str = "sqlite:///./qufin.db"

    # Sign-in sessions: an opaque token in an httpOnly cookie, stored server-side as a hash.
    session_cookie_name: str = "qufin_session"
    session_ttl_hours: int = Field(default=168, ge=1, le=720)
    # Must be true whenever the API is served over HTTPS (enforced in production).
    cookie_secure: bool = False
    # Set to the parent domain (e.g. "qufin.ai") when the web app and API are on subdomains.
    cookie_domain: str | None = None
    # Sign-in and sign-up attempts allowed per client IP and email in each window.
    auth_rate_limit: int = Field(default=10, ge=1)
    auth_rate_window_seconds: int = Field(default=900, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS origins must be listed explicitly; '*' is not allowed")
        return value

    @model_validator(mode="after")
    def secure_cookies_in_production(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("QUFIN_COOKIE_SECURE must be true in production")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
