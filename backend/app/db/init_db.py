from sqlalchemy import inspect, text

from app.db.database import Base, engine
from app.models import (
    company_daily_summary,
    intelligence_snapshot,
    job,
    job_claim,
    market_intelligence_fact,
    market_intelligence_snapshot,
)


def init_db() -> None:
    _ = (
        job,
        company_daily_summary,
        job_claim,
        intelligence_snapshot,
        market_intelligence_fact,
        market_intelligence_snapshot,
    )
    Base.metadata.create_all(bind=engine)
    _ensure_job_region_column()
    _ensure_job_region_index()
    _ensure_region_column("market_intelligence_snapshots")
    _ensure_region_index("market_intelligence_snapshots", "ix_market_intelligence_snapshots_region")
    _ensure_region_column("market_intelligence_facts")
    _ensure_region_index("market_intelligence_facts", "ix_market_intelligence_facts_region")
    _ensure_json_object_column("market_intelligence_facts", "profile_payload")


def _ensure_job_region_column() -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    if any(column["name"] == "region" for column in inspector.get_columns("jobs")):
        return

    dialect = engine.dialect.name
    statement = (
        "ALTER TABLE jobs ADD COLUMN region VARCHAR(32) DEFAULT 'global' NOT NULL"
        if dialect == "sqlite"
        else "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS region VARCHAR(32) DEFAULT 'global' NOT NULL"
    )
    with engine.begin() as connection:
        connection.execute(text(statement))


def _ensure_job_region_index() -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    if not any(column["name"] == "region" for column in inspector.get_columns("jobs")):
        return
    if any(index["name"] == "ix_jobs_region" for index in inspector.get_indexes("jobs")):
        return

    with engine.begin() as connection:
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_region ON jobs (region)"))


def _ensure_region_column(table_name: str) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    if any(column["name"] == "region" for column in inspector.get_columns(table_name)):
        return

    dialect = engine.dialect.name
    statement = (
        f"ALTER TABLE {table_name} ADD COLUMN region VARCHAR(32) DEFAULT 'global' NOT NULL"
        if dialect == "sqlite"
        else f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS region VARCHAR(32) DEFAULT 'global' NOT NULL"
    )
    with engine.begin() as connection:
        connection.execute(text(statement))


def _ensure_region_index(table_name: str, index_name: str) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    if not any(column["name"] == "region" for column in inspector.get_columns(table_name)):
        return
    if any(index["name"] == index_name for index in inspector.get_indexes(table_name)):
        return

    with engine.begin() as connection:
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} (region)"))


def _ensure_json_object_column(table_name: str, column_name: str) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    if any(column["name"] == column_name for column in inspector.get_columns(table_name)):
        return

    dialect = engine.dialect.name
    if dialect == "sqlite":
        statement = f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSON DEFAULT '{{}}' NOT NULL"
    elif dialect == "postgresql":
        statement = (
            f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} "
            "JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    else:
        statement = f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSON DEFAULT '{{}}' NOT NULL"
    with engine.begin() as connection:
        connection.execute(text(statement))
