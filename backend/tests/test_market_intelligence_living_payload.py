import json
from datetime import date, datetime, timedelta

from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services.market_intelligence_living_payload import build_living_market_report_input


def _add_fact(
    db_session,
    *,
    title: str,
    created_at: datetime,
    posted_at: datetime | None,
    company: str | None = "OpenGradient",
) -> MarketIntelligenceFact:
    fact = MarketIntelligenceFact(
        dedupe_key=f"{title}-{created_at.isoformat()}",
        posted_at=posted_at,
        collected_at=created_at,
        company=company,
        company_normalized=company.lower() if company else None,
        title=title,
        job_function="技术",
        market_theme="AI infra",
        seniority="Senior",
        tech_keywords=["llm"],
        business_keywords=[],
        salary_signal="unknown",
        fact_summary="AI infra | 技术 | Senior | llm",
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(fact)
    db_session.commit()
    db_session.refresh(fact)
    return fact


def _add_living_snapshot(db_session, *, generated_at: datetime) -> MarketIntelligenceSnapshot:
    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=generated_at.date(),
        generated_at=generated_at,
        window_days=180,
        market_signal_payload={},
        report_payload={
            "headline": "旧短报告",
            "narrative": "旧 narrative",
            "primary_judgment": {},
            "perspectives": [],
            "trend_cards": [],
            "watchlist": [],
            "living_report": {
                "kind": "living_market_report",
                "schema_version": "living-market-report-v1",
                "version": 1,
                "mode": "baseline_seed",
                "previous_snapshot_id": None,
                "seed_window_days": 180,
                "generated_at": generated_at.isoformat(),
                "executive_summary": "上一版摘要",
                "sections": [],
                "claims": [
                    {
                        "claim_id": "c1",
                        "status": "new",
                        "claim": "AI infra 保持可见。",
                        "confidence": "medium",
                        "evidence_ids": ["e1"],
                    }
                ],
                "watchlist": [],
                "data_quality": {},
            },
        },
        model_name=None,
        status="success",
        error_message=None,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def test_build_living_market_report_input_builds_baseline_windows(db_session):
    now = datetime(2026, 4, 27, 10, 0, 0)
    _add_fact(db_session, title="Recent AI Infra Engineer", created_at=now, posted_at=now - timedelta(days=2))
    _add_fact(db_session, title="Older AI Infra Engineer", created_at=now, posted_at=now - timedelta(days=120))

    payload = build_living_market_report_input(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
    )

    assert payload["report_task"]["mode"] == "initial"
    assert payload["previous_report"] is None
    assert payload["market_windows"]["7d"]["job_count"] == 1
    assert payload["market_windows"]["180d"]["job_count"] == 2
    assert payload["data_quality"]["sample_count"] == 2
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ["canonical_url", "source_name", "full_description", "赏金", "认领", "bd_entry"]:
        assert forbidden not in serialized


def test_build_living_market_report_input_uses_created_at_watermark_for_new_facts(db_session):
    previous = _add_living_snapshot(db_session, generated_at=datetime(2026, 4, 20, 10, 0, 0))
    _add_fact(
        db_session,
        title="Oldly Created Recently Posted",
        created_at=datetime(2026, 4, 19, 10, 0, 0),
        posted_at=datetime(2026, 4, 26, 10, 0, 0),
    )
    new_fact = _add_fact(
        db_session,
        title="Newly Created Old Posting",
        created_at=datetime(2026, 4, 21, 10, 0, 0),
        posted_at=datetime(2026, 1, 30, 10, 0, 0),
    )

    payload = build_living_market_report_input(
        db_session,
        mode="update",
        days=180,
        snapshot_date=date(2026, 4, 27),
        previous_snapshot=previous,
    )

    assert payload["report_task"]["mode"] == "update"
    assert payload["previous_report"]["version"] == 1
    assert [fact["title"] for fact in payload["new_facts"]] == [new_fact.title]
