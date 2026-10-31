"""Run the Alembic migrations from code (app startup in development, tests).

Deployments run `uv run alembic upgrade head` as their own step and set QUFIN_AUTO_MIGRATE=false.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

API_ROOT = Path(__file__).resolve().parents[2]
# The revision that matches databases created before migrations existed (create_all).
BASELINE_REVISION = "0001"


def alembic_config() -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.attributes["configure_logger"] = False
    return config


def upgrade_to_head(engine: Engine) -> None:
    with engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables and "users" in tables:
            # A local database from before migrations: its tables match the baseline.
            command.stamp(config, BASELINE_REVISION)
        command.upgrade(config, "head")
