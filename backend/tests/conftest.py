from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, get_db
from app.main import app
from app.models import company_daily_summary, intelligence_snapshot, job, job_claim


@pytest.fixture()
def test_session_factory() -> Generator[sessionmaker, None, None]:
    _ = (job, company_daily_summary, intelligence_snapshot, job_claim)
    runtime_dir = Path(__file__).resolve().parents[1] / ".pytest-runtime"
    runtime_dir.mkdir(exist_ok=True)
    db_path = runtime_dir / f"test-{uuid4().hex}.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if db_path.exists():
            db_path.unlink()


@pytest.fixture()
def db_session(test_session_factory: sessionmaker) -> Generator[Session, None, None]:
    db = test_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(test_session_factory: sessionmaker) -> Generator[TestClient, None, None]:

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
