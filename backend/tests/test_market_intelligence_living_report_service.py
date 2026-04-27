from datetime import date, datetime, timedelta

from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services import market_intelligence_living_report
from app.services import market_intelligence_living_report_service
from app.services.market_intelligence_living_report_service import generate_living_market_report


def _add_fact(db_session, *, title: str, created_at: datetime) -> None:
    db_session.add(
        MarketIntelligenceFact(
            dedupe_key=f"{title}-{created_at.isoformat()}",
            posted_at=created_at - timedelta(days=1),
            collected_at=created_at,
            company="OpenGradient",
            company_normalized="opengradient",
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
    )
    db_session.commit()


def _fake_report(input_payload, *, version, mode, previous_snapshot_id, generated_at):
    evidence_id = input_payload["representative_samples"][0]["evidence_id"]
    return {
        "kind": "living_market_report",
        "schema_version": "living-market-report-v1",
        "headline": "AI infra 保持结构性可见",
        "version": version,
        "mode": mode,
        "previous_snapshot_id": previous_snapshot_id,
        "seed_window_days": 180,
        "generated_at": generated_at.isoformat(),
        "executive_summary": "AI infra 基线报告。",
        "sections": [
            {"section_id": "market_structure", "title": "市场结构", "body": "body", "claim_ids": ["c1"]},
            {"section_id": "demand_shifts", "title": "需求变化", "body": "body", "claim_ids": ["c2"]},
            {"section_id": "company_patterns", "title": "公司与组织信号", "body": "body", "claim_ids": ["c3"]},
            {"section_id": "risk_and_uncertainty", "title": "不确定性", "body": "body", "claim_ids": ["c4"]},
        ],
        "claims": [
            {
                "claim_id": f"c{index}",
                "previous_claim_id": None,
                "status": "new",
                "claim": f"claim {index}",
                "confidence": "low",
                "evidence_ids": [evidence_id],
                "evidence_notes": ["note"],
                "change_reason": "baseline",
            }
            for index in range(1, 5)
        ],
        "watchlist": [{"topic": "AI infra", "why_watch": "watch", "evidence_ids": [evidence_id]}],
        "data_quality": input_payload["data_quality"],
    }


def test_generate_living_market_report_baseline_writes_v1_snapshot(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "success"
    assert snapshot.window_days == 180
    assert snapshot.report_payload["living_report"]["version"] == 1
    assert snapshot.report_payload["living_report"]["mode"] == "baseline_seed"
    assert snapshot.report_payload["headline"] == "AI infra 保持结构性可见"
    assert snapshot.report_payload["narrative"]


def test_generate_living_market_report_baseline_rejects_existing_report(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)
    generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    try:
        generate_living_market_report(
            db_session,
            mode="baseline",
            days=180,
            snapshot_date=date(2026, 4, 28),
            clock=lambda: datetime(2026, 4, 28, 11, 0, 0),
        )
    except ValueError as exc:
        assert "baseline" in str(exc)
    else:
        raise AssertionError("baseline should reject existing living report")


def test_generate_living_market_report_update_writes_next_version(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report_service, "generate_living_market_report_payload", _fake_report)
    first = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    result = generate_living_market_report(
        db_session,
        mode="update",
        days=180,
        snapshot_date=date(2026, 4, 28),
        clock=lambda: datetime(2026, 4, 28, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert snapshot.report_payload["living_report"]["version"] == 2
    assert snapshot.report_payload["living_report"]["mode"] == "incremental_update"
    assert snapshot.report_payload["living_report"]["previous_snapshot_id"] == first["snapshot_id"]


def test_generate_living_market_report_marks_invalid_llm_as_fallback(db_session, monkeypatch):
    _add_fact(db_session, title="AI Infra Engineer", created_at=datetime(2026, 4, 27, 10, 0, 0))
    monkeypatch.setattr(market_intelligence_living_report, "should_use_llm", lambda: True)
    monkeypatch.setattr(market_intelligence_living_report, "request_structured_json", lambda messages: "{invalid json")

    result = generate_living_market_report(
        db_session,
        mode="baseline",
        days=180,
        snapshot_date=date(2026, 4, 27),
        clock=lambda: datetime(2026, 4, 27, 11, 0, 0),
    )

    snapshot = db_session.get(MarketIntelligenceSnapshot, result["snapshot_id"])
    assert result["status"] == "fallback"
    assert snapshot.status == "fallback"
    assert "LLM report failed validation" in snapshot.error_message
    assert snapshot.report_payload["living_report"]["claims"][0]["change_reason"].startswith("LLM 不可用")
