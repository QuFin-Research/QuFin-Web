from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.stores.db import Base, import_models, make_engine
from app.stores.migrate import upgrade_to_head


def test_migrations_build_the_same_schema_as_the_models():
    engine = make_engine("sqlite://")
    upgrade_to_head(engine)
    import_models()
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_upgrade_is_idempotent():
    engine = make_engine("sqlite://")
    upgrade_to_head(engine)
    upgrade_to_head(engine)
    with engine.connect() as conn:
        version = conn.execute(text("select version_num from alembic_version")).scalar()
    assert version == "0004"


def test_database_from_before_migrations_is_adopted():
    # Local databases created by create_all before Alembic: same tables as revision 0001.
    engine = make_engine("sqlite://")
    import_models()
    legacy = [Base.metadata.tables[name] for name in ("users", "sessions", "decisions")]
    Base.metadata.create_all(engine, tables=legacy)
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into users (id, email, password_hash, created_at) "
                "values ('u1', 'a@example.com', 'x', '2026-01-01')"
            )
        )

    upgrade_to_head(engine)

    tables = set(inspect(engine).get_table_names())
    assert {"macro_series", "macro_observations", "cot_reports", "alembic_version"} <= tables
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from users")).scalar() == 1
