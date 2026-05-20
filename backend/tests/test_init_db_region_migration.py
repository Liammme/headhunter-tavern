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
