from datetime import date, datetime, timedelta
import json
from importlib import reload

from app.models import Job, MarketIntelligenceSnapshot
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


def test_build_home_payload_prefers_success_market_intelligence_snapshot(db_session):
    job_time = datetime.now().replace(microsecond=0) - timedelta(days=1)
    db_session.add(
        Job(
            canonical_url="https://jobs.example.com/opengradient/staff-ai-engineer",
            source_name="test",
            title="Staff AI Engineer",
            company="OpenGradient",
            company_normalized="opengradient",
            description="test",
            posted_at=job_time,
            collected_at=job_time,
            bounty_grade="high",
            signal_tags={"display_tags": ["AI", "Senior"]},
        )
    )
    db_session.add(
        MarketIntelligenceSnapshot(
            snapshot_date=date(2026, 4, 25),
            generated_at=datetime(2026, 4, 26, 15, 0, 0),
            window_days=90,
            market_signal_payload={},
            report_payload={
                "headline": "Market snapshot headline",
                "narrative": "Market snapshot narrative",
                "primary_judgment": {"claim": "Market snapshot summary"},
                "trend_cards": [{"judgment": "Market snapshot finding"}],
                "watchlist": ["Market snapshot action"],
            },
            model_name=None,
            status="success",
            error_message=None,
        )
    )
    db_session.commit()

    payload = build_home_payload(db_session)

    assert payload["intelligence"]["headline"] == "Market snapshot headline"
    assert payload["intelligence"]["summary"] == "Market snapshot summary"
    assert payload["intelligence"]["generated_at"] == "2026-04-26T15:00:00"
    assert payload["meta"]["generated_at"] == job_time.isoformat()
    assert payload["days"][0]["companies"][0]["company"] == "OpenGradient"


def test_build_home_payload_reads_configured_jdtrust_assessment_jsonl(db_session, tmp_path, monkeypatch):
    now = datetime.now().replace(microsecond=0)
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/staff-ai-engineer",
        source_name="test",
        title="Staff AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="test",
        posted_at=now,
        collected_at=now,
        bounty_grade="high",
        signal_tags={"display_tags": ["AI", "Senior"]},
    )
    db_session.add(job)
    db_session.commit()

    assessment_path = tmp_path / "jdtrust.jsonl"
    assessment_path.write_text(
        json.dumps(
            {
                "legacy_job_id": job.id,
                "canonical_url": "https://jobs.example.com/opengradient/staff-ai-engineer",
                "source_name": "test",
                "title": "Staff AI Engineer",
                "company": "OpenGradient",
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 58,
                    "reason_codes": ["weak_job_page_evidence"],
                    "recommended_checks": ["核对官网招聘页"],
                    "evidence_refs": ["canonical_post"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.home_feed.settings.bounty_pool_jdtrust_read_enabled", True)
    monkeypatch.setattr("app.services.home_feed.settings.bounty_pool_jdtrust_assessments_path", str(assessment_path))

    payload = build_home_payload(db_session)

    assert payload["days"][0]["companies"][0]["jd_trust"] == {
        "legacy_job_id": job.id,
        "canonical_url": "https://jobs.example.com/opengradient/staff-ai-engineer",
        "source_name": "test",
        "title": "Staff AI Engineer",
        "company": "OpenGradient",
        "risk_level": "needs_review",
        "trust_score": 58,
        "reason_codes": ["weak_job_page_evidence"],
        "recommended_checks": ["核对官网招聘页"],
        "evidence_refs": ["canonical_post"],
        "domain_warnings": [],
        "verification_tags": [],
    }


def test_settings_default_database_url_points_to_backend_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core import config

    reloaded = reload(config)

    try:
        assert reloaded.settings.database_url == f"sqlite+pysqlite:///{reloaded.DEFAULT_SQLITE_PATH}"
    finally:
        reload(config)
