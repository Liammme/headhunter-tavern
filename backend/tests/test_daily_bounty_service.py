from datetime import datetime

from app.models import Job
from app.services.daily_bounty_service import run_daily_bounty_generation


def _clock(*values):
    ticks = iter(values)
    return lambda: next(ticks)


def _home_payload(today_companies):
    return {
        "intelligence": {"headline": "test", "summary": "test", "findings": [], "actions": []},
        "days": [
            {
                "bucket": "today",
                "label": "今天",
                "companies": today_companies,
            },
            {"bucket": "yesterday", "label": "昨天", "companies": []},
        ],
    }


def _job(canonical_url, *, company="OpenGradient"):
    return Job(
        canonical_url=canonical_url,
        source_name="greenhouse",
        title="Protocol Engineer",
        company=company,
        company_normalized=company.lower(),
        collected_at=datetime.now(),
        signal_tags={},
    )


def test_run_daily_bounty_generation_returns_crawl_and_today_summary(db_session, monkeypatch):
    snapshot_calls = []

    def fake_trigger_crawl(db):
        assert db is db_session
        return {
            "status": "triggered",
            "fetched_jobs": 5,
            "new_jobs": 3,
            "source_stats": {"greenhouse": 2, "lever": 3},
            "errors": [],
        }

    def fake_get_home_payload(db):
        assert db is db_session
        return _home_payload(
            [
                {"company": "OpenGradient", "total_jobs": 2, "jobs": [{}, {}]},
                {"company": "ChainSight", "total_jobs": 1, "jobs": [{}]},
            ]
        )

    def fake_generate_daily_market_intelligence_snapshot(db):
        assert db is db_session
        snapshot_calls.append(db)
        return {"status": "success", "snapshot_id": 1}

    monkeypatch.setattr("app.services.daily_bounty_service.trigger_crawl", fake_trigger_crawl)
    monkeypatch.setattr("app.services.daily_bounty_service.get_home_payload", fake_get_home_payload)
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        fake_generate_daily_market_intelligence_snapshot,
        raising=False,
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 1)),
    )

    assert summary == {
        "status": "completed",
        "started_at": "2026-04-21T08:00:00",
        "finished_at": "2026-04-21T08:01:00",
        "fetched_jobs": 5,
        "new_jobs": 3,
        "source_stats": {"greenhouse": 2, "lever": 3},
        "errors": [],
        "today_company_count": 2,
        "today_job_count": 3,
    }
    assert snapshot_calls == [db_session]


def test_run_daily_bounty_generation_keeps_partial_failures_observable(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {
            "status": "triggered",
            "fetched_jobs": 2,
            "new_jobs": 1,
            "source_stats": {"greenhouse": 2},
            "errors": ["lever: timeout"],
        },
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 2, "jobs": [{}, {}]}]),
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        lambda db: {"status": "success", "snapshot_id": 1},
        raising=False,
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    assert summary["status"] == "completed_with_errors"
    assert summary["errors"] == ["lever: timeout"]
    assert summary["source_stats"] == {"greenhouse": 2}
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 2


def test_run_daily_bounty_generation_reports_market_snapshot_failure(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {
            "status": "triggered",
            "fetched_jobs": 2,
            "new_jobs": 2,
            "source_stats": {"greenhouse": 2},
            "errors": [],
        },
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        lambda db: {"status": "failed", "error": "model timed out"},
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 2, "jobs": [{}, {}]}]),
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    assert summary["status"] == "completed_with_errors"
    assert summary["errors"] == ["market_intelligence: model timed out"]
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 2


def test_run_daily_bounty_generation_reports_market_snapshot_exception(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {
            "status": "triggered",
            "fetched_jobs": 2,
            "new_jobs": 2,
            "source_stats": {"greenhouse": 2},
            "errors": [],
        },
    )

    def raise_snapshot_error(db):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        raise_snapshot_error,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 2, "jobs": [{}, {}]}]),
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    assert summary["status"] == "completed_with_errors"
    assert summary["errors"] == ["market_intelligence: provider unavailable"]
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 2


def test_run_daily_bounty_generation_redacts_market_snapshot_exception_secrets(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {
            "status": "triggered",
            "fetched_jobs": 2,
            "new_jobs": 2,
            "source_stats": {"greenhouse": 2},
            "errors": [],
        },
    )

    def raise_secret_error(db):
        raise RuntimeError(
            "provider failed: "
            "sk-test-redact-me "
            "OPENAI_API_KEY=env-openai-secret "
            "api_key=plain-api-secret "
            "access_token=plain-access-token-secret "
            "token: colon-token-secret "
            "password=plain-password-secret "
            "password: colon-password-secret "
            "Authorization: Bearer bearer-token-secret "
            "postgresql://user:db-password-secret@example.com:5432/app "
            "postgres://user:postgres-password-secret@example.com:5432/app "
            "mysql://user:mysql-password-secret@example.com:3306/app"
        )

    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        raise_secret_error,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 2, "jobs": [{}, {}]}]),
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    error_text = "\n".join(summary["errors"])
    assert summary["status"] == "completed_with_errors"
    assert "market_intelligence: provider failed:" in error_text
    assert "OPENAI_API_KEY=[redacted]" in error_text
    assert "api_key=[redacted]" in error_text
    assert "access_token=[redacted]" in error_text
    assert "token: [redacted]" in error_text
    assert "password=[redacted]" in error_text
    assert "password: [redacted]" in error_text
    assert "Authorization: Bearer [redacted]" in error_text
    assert "sk-test-redact-me" not in error_text
    assert "env-openai-secret" not in error_text
    assert "plain-api-secret" not in error_text
    assert "plain-access-token-secret" not in error_text
    assert "colon-token-secret" not in error_text
    assert "plain-password-secret" not in error_text
    assert "colon-password-secret" not in error_text
    assert "bearer-token-secret" not in error_text
    assert "db-password-secret" not in error_text
    assert "postgres-password-secret" not in error_text
    assert "mysql-password-secret" not in error_text
    assert "postgresql://user:db-password-secret" not in error_text
    assert "postgres://user:postgres-password-secret" not in error_text
    assert "mysql://user:mysql-password-secret" not in error_text
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 2


def test_run_daily_bounty_generation_rolls_back_market_snapshot_db_error(db_session, monkeypatch):
    def fake_trigger_crawl(db):
        db.add(_job("https://example.com/jobs/1"))
        db.commit()
        return {
            "status": "triggered",
            "fetched_jobs": 1,
            "new_jobs": 1,
            "source_stats": {"greenhouse": 1},
            "errors": [],
        }

    def fail_snapshot_with_db_error(db):
        db.add(_job("https://example.com/jobs/1"))
        try:
            db.flush()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("snapshot db write failed") from exc

    monkeypatch.setattr("app.services.daily_bounty_service.trigger_crawl", fake_trigger_crawl)
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        fail_snapshot_with_db_error,
        raising=False,
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    assert summary["status"] == "completed_with_errors"
    assert summary["errors"] == ["market_intelligence: snapshot db write failed"]
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 1


def test_run_daily_bounty_generation_reports_failure_without_hiding_existing_home(db_session, monkeypatch):
    snapshot_calls = []

    def fake_trigger_crawl(db):
        raise RuntimeError("network unavailable")

    def fake_generate_daily_market_intelligence_snapshot(db):
        snapshot_calls.append(db)
        return {"status": "success", "snapshot_id": 1}

    monkeypatch.setattr("app.services.daily_bounty_service.trigger_crawl", fake_trigger_crawl)
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        fake_generate_daily_market_intelligence_snapshot,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "ExistingCo", "total_jobs": 4, "jobs": [{}, {}, {}, {}]}]),
    )

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 3)),
    )

    assert summary["status"] == "failed"
    assert summary["fetched_jobs"] == 0
    assert summary["new_jobs"] == 0
    assert summary["source_stats"] == {}
    assert summary["errors"] == ["daily_bounty: network unavailable"]
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 4
    assert snapshot_calls == []
