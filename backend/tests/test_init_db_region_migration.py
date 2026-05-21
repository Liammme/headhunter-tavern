from sqlalchemy import create_engine, inspect, text

from app.db import init_db as init_db_module


def test_init_db_adds_region_column_and_index_to_existing_jobs_table(tmp_path, monkeypatch):
    db_path = tmp_path / "existing.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY,
                    canonical_url VARCHAR(1024) NOT NULL UNIQUE,
                    source_name VARCHAR(64) NOT NULL
                )
                """
            )
        )

    monkeypatch.setattr(init_db_module, "engine", engine)

    init_db_module.init_db()

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    indexes = {index["name"] for index in inspector.get_indexes("jobs")}

    assert "region" in columns
    assert "ix_jobs_region" in indexes


def test_init_db_adds_region_columns_and_indexes_idempotently(tmp_path, monkeypatch):
    db_path = tmp_path / "existing-market.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE market_intelligence_snapshots (
                    id INTEGER PRIMARY KEY,
                    snapshot_date DATE NOT NULL,
                    generated_at DATETIME NOT NULL,
                    window_days INTEGER NOT NULL,
                    market_signal_payload JSON NOT NULL,
                    report_payload JSON NOT NULL,
                    status VARCHAR(32) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE market_intelligence_facts (
                    id INTEGER PRIMARY KEY,
                    dedupe_key VARCHAR(64) NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    collected_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

    monkeypatch.setattr(init_db_module, "engine", engine)

    init_db_module.init_db()
    init_db_module.init_db()

    inspector = inspect(engine)
    snapshot_columns = {column["name"] for column in inspector.get_columns("market_intelligence_snapshots")}
    fact_columns = {column["name"] for column in inspector.get_columns("market_intelligence_facts")}
    snapshot_indexes = {index["name"] for index in inspector.get_indexes("market_intelligence_snapshots")}
    fact_indexes = {index["name"] for index in inspector.get_indexes("market_intelligence_facts")}

    assert "region" in snapshot_columns
    assert "region" in fact_columns
    assert "ix_market_intelligence_snapshots_region" in snapshot_indexes
    assert "ix_market_intelligence_facts_region" in fact_indexes
