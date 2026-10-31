from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from QUFIN_* environment variables or a local .env.

    Nothing secret has a default: anything sensitive must come from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="QUFIN_", env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    database_url: str = "sqlite:///./qufin.db"

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

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
