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
