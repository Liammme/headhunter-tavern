from datetime import datetime, timedelta

from app.models import MarketIntelligenceSnapshot
from app.services import market_intelligence_living_refresh_service as refresh_service
from app.services.region import GLOBAL_REGION


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
        lambda db, days, dry_run=False, collected_at=None, region=GLOBAL_REGION, adapters=None: {
            "inserted": 2,
            "days": days,
        },
    )

    def fake_generate(db, *, mode, days, snapshot_date, clock, region=GLOBAL_REGION):
        calls.append((mode, days, snapshot_date, clock(), region))
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
    assert calls == [("auto", 180, now.date(), now, GLOBAL_REGION)]


def test_refresh_skips_when_latest_success_is_fresh(db_session, monkeypatch):
    now = datetime(2026, 4, 27, 15, 30, 0)
    latest = _success_snapshot(db_session, generated_at=now - timedelta(days=2))
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run=False, collected_at=None, region=GLOBAL_REGION, adapters=None: {
            "inserted": 0,
            "days": days,
        },
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
        lambda db, days, dry_run=False, collected_at=None, region=GLOBAL_REGION, adapters=None: {
            "inserted": 1,
            "days": days,
        },
    )

    def fake_generate(db, *, mode, days, snapshot_date, clock, region=GLOBAL_REGION):
        calls.append((mode, days, snapshot_date, clock(), region))
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
    assert calls == [("auto", 180, now.date(), now, GLOBAL_REGION)]


def test_refresh_generates_talentverse_variant_after_successful_global_report(db_session, monkeypatch):
    calls = []

    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 101},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: calls.append(raw_snapshot_id) or {"status": "published", "report_id": 201},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert calls == [101]
    assert result["talentverse_report"] == {"status": "published", "report_id": 201}


def test_refresh_does_not_generate_talentverse_variant_for_japan(db_session, monkeypatch):
    calls = []

    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 102},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: calls.append(raw_snapshot_id) or {"status": "published"},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session, region="japan")

    assert calls == []
    assert "talentverse_report" not in result


def test_refresh_records_talentverse_failed_without_failing_raw_report(db_session, monkeypatch):
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 103},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: {"status": "failed", "error": "provider unavailable"},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert result["status"] == "success"
    assert result["talentverse_report"] == {"status": "failed", "error": "provider unavailable"}


def test_refresh_catches_talentverse_exception_without_failing_raw_report(db_session, monkeypatch):
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 104},
    )

    def raise_from_talentverse(db, raw_snapshot_id):
        raise RuntimeError("unexpected talentverse failure")

    monkeypatch.setattr(refresh_service, "generate_talentverse_report_for_snapshot", raise_from_talentverse)

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert result["status"] == "success"
    assert result["talentverse_report"]["status"] == "failed"
    assert "unexpected talentverse failure" in result["talentverse_report"]["error"]
