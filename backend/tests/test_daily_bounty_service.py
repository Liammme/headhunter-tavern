from datetime import datetime

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


def test_run_daily_bounty_generation_returns_crawl_and_today_summary(db_session, monkeypatch):
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

    monkeypatch.setattr("app.services.daily_bounty_service.trigger_crawl", fake_trigger_crawl)
    monkeypatch.setattr("app.services.daily_bounty_service.get_home_payload", fake_get_home_payload)

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

    summary = run_daily_bounty_generation(
        db_session,
        clock=_clock(datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 2)),
    )

    assert summary["status"] == "completed_with_errors"
    assert summary["errors"] == ["lever: timeout"]
    assert summary["source_stats"] == {"greenhouse": 2}
    assert summary["today_company_count"] == 1
    assert summary["today_job_count"] == 2


def test_run_daily_bounty_generation_reports_failure_without_hiding_existing_home(db_session, monkeypatch):
    def fake_trigger_crawl(db):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.services.daily_bounty_service.trigger_crawl", fake_trigger_crawl)
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
