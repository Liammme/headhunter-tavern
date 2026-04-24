from datetime import datetime
from importlib import reload

from app.models import Job
from app.services.home_feed import build_home_payload


def test_build_home_payload_uses_latest_job_collection_time_as_generated_at(db_session):
    db_session.add(
        Job(
            canonical_url="https://jobs.example.com/opengradient/staff-ai-engineer",
            source_name="test",
            title="Staff AI Engineer",
            company="OpenGradient",
            company_normalized="opengradient",
            description="test",
            posted_at=datetime(2026, 4, 22, 9, 0, 0),
            collected_at=datetime(2026, 4, 22, 14, 32, 21),
            bounty_grade="high",
            signal_tags={"display_tags": ["AI", "Senior"]},
        )
    )
    db_session.commit()

    payload = build_home_payload(db_session)

    assert payload["meta"]["generated_at"] == "2026-04-22T14:32:21"
    assert payload["intelligence"]["generated_at"] == "2026-04-22T14:32:21"


def test_settings_default_database_url_points_to_backend_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core import config

    reloaded = reload(config)

    try:
        assert reloaded.settings.database_url == f"sqlite+pysqlite:///{reloaded.DEFAULT_SQLITE_PATH}"
    finally:
        reload(config)
