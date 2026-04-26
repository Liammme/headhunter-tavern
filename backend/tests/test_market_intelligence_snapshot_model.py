from datetime import date, datetime

from sqlalchemy import select

from app.models import MarketIntelligenceSnapshot


def test_market_intelligence_snapshot_round_trips_payloads(db_session):
    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=date(2026, 4, 26),
        generated_at=datetime(2026, 4, 26, 14, 0, 0),
        window_days=90,
        market_signal_payload={"windows": {"30d": {"job_count": 12}}},
        report_payload={"headline": "AI infra hiring is rising", "narrative": "30d signal"},
        model_name="deepseek-v4-flash",
        status="success",
        error_message=None,
    )
    db_session.add(snapshot)
    db_session.commit()

    loaded = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()

    assert loaded.snapshot_date == date(2026, 4, 26)
    assert loaded.window_days == 90
    assert loaded.status == "success"
    assert loaded.market_signal_payload["windows"]["30d"]["job_count"] == 12
    assert loaded.report_payload["headline"] == "AI infra hiring is rising"
