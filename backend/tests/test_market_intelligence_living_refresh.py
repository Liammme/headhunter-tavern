from datetime import datetime, timedelta

from app.models import MarketIntelligenceSnapshot
from app.services import market_intelligence_living_refresh_service as refresh_service


def _success_snapshot(db_session, *, generated_at: datetime) -> MarketIntelligenceSnapshot:
    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=generated_at.date(),
        generated_at=generated_at,
        window_days=180,
        market_signal_payload={},
        report_payload={
            "headline": "Living report",
            "narrative": "Summary",
            "living_report": {
                "kind": "living_market_report",
                "schema_version": "living-market-report-v1",
                "version": 1,
                "sections": [],
                "claims": [],
                "watchlist": [],
                "data_quality": {},
            },
        },
        status="success",
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def test_refresh_generates_when_no_success_report_exists(db_session, monkeypatch):
    calls = []
    now = datetime(2026, 4, 27, 15, 30, 0)
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run=False, collected_at=None: {"inserted": 2, "days": days},
    )

    def fake_generate(db, *, mode, days, snapshot_date, clock):
        calls.append((mode, days, snapshot_date, clock()))
        return {"status": "success", "snapshot_id": 10}

    monkeypatch.setattr(refresh_service, "generate_living_market_report", fake_generate)

    result = refresh_service.refresh_living_market_report_if_due(
        db_session,
        days=180,
        min_age_days=3,
        clock=lambda: now,
    )

    assert result["status"] == "success"
    assert result["facts"]["inserted"] == 2
    assert calls == [("auto", 180, now.date(), now)]


def test_refresh_skips_when_latest_success_is_fresh(db_session, monkeypatch):
    now = datetime(2026, 4, 27, 15, 30, 0)
    latest = _success_snapshot(db_session, generated_at=now - timedelta(days=2))
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run=False, collected_at=None: {"inserted": 0, "days": days},
    )

    def fail_generate(*_args, **_kwargs):
        raise AssertionError("fresh report should not regenerate")

    monkeypatch.setattr(refresh_service, "generate_living_market_report", fail_generate)

    result = refresh_service.refresh_living_market_report_if_due(
        db_session,
        days=180,
        min_age_days=3,
        clock=lambda: now,
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "latest_success_fresh"
    assert result["latest_snapshot_id"] == latest.id
    assert result["next_due_at"] == "2026-04-28T15:30:00"
    assert result["facts"]["inserted"] == 0


def test_refresh_generates_when_latest_success_is_due(db_session, monkeypatch):
    now = datetime(2026, 4, 27, 15, 30, 0)
    _success_snapshot(db_session, generated_at=datetime(2026, 4, 24, 19, 30, 0))
    calls = []
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run=False, collected_at=None: {"inserted": 1, "days": days},
    )

    def fake_generate(db, *, mode, days, snapshot_date, clock):
        calls.append((mode, days, snapshot_date, clock()))
        return {"status": "success", "snapshot_id": 11}

    monkeypatch.setattr(refresh_service, "generate_living_market_report", fake_generate)

    result = refresh_service.refresh_living_market_report_if_due(
        db_session,
        days=180,
        min_age_days=3,
        clock=lambda: now,
    )

    assert result["status"] == "success"
    assert result["snapshot_id"] == 11
    assert result["facts"]["inserted"] == 1
    assert calls == [("auto", 180, now.date(), now)]
