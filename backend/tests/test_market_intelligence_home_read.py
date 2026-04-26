from datetime import date, datetime

import pytest

from app.models import MarketIntelligenceSnapshot
from app.services.market_intelligence_read_service import load_latest_market_intelligence_for_home


def _report_payload(
    *,
    headline: str = "Market headline",
    narrative: str = "Market narrative",
    claim: str = "Primary claim",
) -> dict:
    return {
        "headline": headline,
        "narrative": narrative,
        "primary_judgment": {"claim": claim},
        "trend_cards": [
            {"judgment": "First trend judgment"},
            {"judgment": "Second trend judgment"},
        ],
        "watchlist": ["First watch item", "Second watch item"],
    }


def _add_snapshot(
    db_session,
    *,
    snapshot_date: date = date(2026, 4, 26),
    generated_at: datetime = datetime(2026, 4, 26, 10, 0, 0),
    status: str = "success",
    report_payload: dict | None = None,
) -> MarketIntelligenceSnapshot:
    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=snapshot_date,
        generated_at=generated_at,
        window_days=90,
        market_signal_payload={},
        report_payload=report_payload if report_payload is not None else _report_payload(),
        model_name=None,
        status=status,
        error_message="model failed" if status == "failed" else None,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def test_load_latest_market_intelligence_skips_failed_snapshot(db_session):
    _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 9, 0, 0),
        report_payload=_report_payload(headline="Successful headline", narrative="Successful narrative"),
    )
    _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 10, 0, 0),
        status="failed",
        report_payload=_report_payload(headline="Failed headline", narrative="Failed narrative"),
    )

    payload = load_latest_market_intelligence_for_home(db_session)

    assert payload is not None
    assert payload["headline"] == "Successful headline"
    assert payload["narrative"] == "Successful narrative"


def test_load_latest_market_intelligence_uses_generated_at_then_id_order(db_session):
    _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 9, 0, 0),
        report_payload=_report_payload(headline="Older headline", narrative="Older narrative"),
    )
    lower_id = _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 10, 0, 0),
        report_payload=_report_payload(headline="Lower id headline", narrative="Lower id narrative"),
    )
    higher_id = _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 10, 0, 0),
        report_payload=_report_payload(headline="Higher id headline", narrative="Higher id narrative"),
    )

    payload = load_latest_market_intelligence_for_home(db_session)

    assert higher_id.id > lower_id.id
    assert payload is not None
    assert payload["headline"] == "Higher id headline"


@pytest.mark.parametrize(
    "report_payload",
    [
        {"headline": "", "narrative": "Narrative"},
        {"headline": "Headline", "narrative": " "},
    ],
)
def test_load_latest_market_intelligence_returns_none_when_latest_success_missing_text(
    db_session,
    report_payload,
):
    _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 9, 0, 0),
        report_payload=_report_payload(headline="Older valid headline", narrative="Older valid narrative"),
    )
    _add_snapshot(
        db_session,
        generated_at=datetime(2026, 4, 26, 10, 0, 0),
        report_payload=report_payload,
    )

    assert load_latest_market_intelligence_for_home(db_session) is None


def test_load_latest_market_intelligence_returns_home_intelligence_shape(db_session):
    _add_snapshot(
        db_session,
        snapshot_date=date(2026, 4, 25),
        generated_at=datetime(2026, 4, 26, 10, 15, 30, 123456),
        report_payload={
            "headline": "AI infrastructure roles are concentrating",
            "narrative": "AI infrastructure demand is clustering around platform teams.",
            "primary_judgment": {"claim": "Platform AI hiring is the lead signal."},
            "trend_cards": [
                {"judgment": "AI infra roles are showing the clearest demand."},
                {"judgment": "Second card should not be included."},
            ],
            "watchlist": [
                "Watch platform teams with multiple senior openings.",
                "Second watch item should not be included.",
            ],
        },
    )

    payload = load_latest_market_intelligence_for_home(db_session)

    assert payload == {
        "narrative": "AI infrastructure demand is clustering around platform teams.",
        "headline": "AI infrastructure roles are concentrating",
        "summary": "Platform AI hiring is the lead signal.",
        "analysis_version": "market-intelligence-v1",
        "rule_version": "market-intelligence-v1",
        "window_start": None,
        "window_end": "2026-04-25",
        "generated_at": "2026-04-26T10:15:30",
        "findings": ["AI infra roles are showing the clearest demand."],
        "actions": ["Watch platform teams with multiple senior openings."],
    }
