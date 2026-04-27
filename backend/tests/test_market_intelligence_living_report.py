from datetime import date, datetime, timedelta

import pytest

from app.models import MarketIntelligenceSnapshot
from app.services import market_intelligence_living_report
from app.services.market_intelligence_living_report import (
    LivingMarketReportError,
    build_rule_living_market_report,
    generate_living_market_report_payload,
    validate_living_market_report,
)


def _living_input(*, mode: str = "initial") -> dict:
    previous_report = None
    if mode == "update":
        previous_report = {
            "version": 1,
            "summary": "上一版认为 AI infra 是主要结构性需求。",
            "active_claims": [
                {
                    "claim_id": "c1",
                    "claim": "AI infra 需求保持可见。",
                    "confidence": "medium",
                }
            ],
        }
    return {
        "report_task": {
            "report_id": "living-market-report",
            "language": "zh-CN",
            "target_length_words": [1500, 2500],
            "mode": mode,
            "snapshot_date": "2026-04-27",
        },
        "previous_report": previous_report,
        "market_windows": {
            "7d": {"job_count": 2, "theme_counts": {"AI infra": 2}, "function_counts": {"技术": 2}},
            "30d": {"job_count": 4, "theme_counts": {"AI infra": 3}, "function_counts": {"技术": 3}},
            "90d": {"job_count": 6, "theme_counts": {"AI infra": 4}, "function_counts": {"技术": 4}},
            "180d": {"job_count": 8, "theme_counts": {"AI infra": 5}, "function_counts": {"技术": 5}},
        },
        "deltas": {
            "7d_vs_30d": {"theme_counts": {"AI infra": 0.25}},
            "30d_vs_90d": {"theme_counts": {"AI infra": 0.33}},
            "90d_vs_180d": {"theme_counts": {"AI infra": 0.5}},
        },
        "new_facts": [{"evidence_id": "e1", "title": "AI Infra Engineer", "market_theme": "AI infra"}],
        "representative_samples": [
            {
                "evidence_id": "e1",
                "company": "OpenGradient",
                "title": "AI Infra Engineer",
                "posted_date": "2026-04-26",
                "function": "技术",
                "domain": "AI infra",
                "seniority": "Senior",
                "tech_keywords": ["llm"],
                "business_keywords": [],
                "fact_summary": "AI infra | 技术 | Senior | llm",
            }
        ],
        "allowed_evidence_terms": ["e1", "AI infra", "OpenGradient", "技术"],
        "data_quality": {
            "baseline_note": "当前可见岗位的历史基线，不代表完整真实半年历史。",
            "posted_at_fact_count": 8,
            "collected_at_fallback_count": 0,
            "unknown_company_count": 0,
            "sample_count": 8,
        },
    }


def _valid_living_report(*, version: int = 1, mode: str = "baseline_seed") -> dict:
    previous_claim_id = None if version == 1 else "c1"
    status = "new" if version == 1 else "reinforced"
    return {
        "kind": "living_market_report",
        "schema_version": "living-market-report-v1",
        "headline": "AI infra 需求保持克制升温",
        "version": version,
        "mode": mode,
        "previous_snapshot_id": None if version == 1 else 10,
        "seed_window_days": 180,
        "generated_at": "2026-04-27T10:00:00",
        "executive_summary": "AI infra 在 180 天样本中保持可见，短窗没有足够证据说明全面加速。",
        "sections": [
            {
                "section_id": "market_structure",
                "title": "市场结构",
                "body": "AI infra 仍是当前样本里最稳定的结构性主题，判断依据来自 e1。",
                "claim_ids": ["c1"],
            },
            {
                "section_id": "demand_shifts",
                "title": "需求变化",
                "body": "短窗需求没有脱离 180 天基线，判断依据来自 e1。",
                "claim_ids": ["c2"],
            },
            {
                "section_id": "company_patterns",
                "title": "公司与组织信号",
                "body": "OpenGradient 的技术岗位提供了代表性组织信号，判断依据来自 e1。",
                "claim_ids": ["c3"],
            },
            {
                "section_id": "risk_and_uncertainty",
                "title": "不确定性",
                "body": "样本只代表当前可见岗位池，判断依据来自 e1。",
                "claim_ids": ["c4"],
            },
        ],
        "claims": [
            {
                "claim_id": "c1",
                "previous_claim_id": previous_claim_id,
                "status": status,
                "claim": "AI infra 是最稳定的结构性主题。",
                "confidence": "medium",
                "evidence_ids": ["e1"],
                "evidence_notes": ["AI infra 在多个窗口保持可见。"],
                "change_reason": "由 180 天样本建立基线。",
            },
            {
                "claim_id": "c2",
                "previous_claim_id": None,
                "status": "new",
                "claim": "短期变化不足以证明全面升温。",
                "confidence": "low",
                "evidence_ids": ["e1"],
                "evidence_notes": ["7d 样本仍较小。"],
                "change_reason": "新增保守判断。",
            },
            {
                "claim_id": "c3",
                "previous_claim_id": None,
                "status": "new",
                "claim": "技术岗位承担主要可见需求。",
                "confidence": "medium",
                "evidence_ids": ["e1"],
                "evidence_notes": ["技术函数在窗口中可见。"],
                "change_reason": "新增组织判断。",
            },
            {
                "claim_id": "c4",
                "previous_claim_id": None,
                "status": "new",
                "claim": "样本质量限制需要保留。",
                "confidence": "low",
                "evidence_ids": ["e1"],
                "evidence_notes": ["当前样本来自结构化事实。"],
                "change_reason": "新增不确定性判断。",
            },
        ],
        "watchlist": [
            {
                "topic": "AI infra",
                "why_watch": "后续需要验证 30 天窗口是否持续扩大。",
                "evidence_ids": ["e1"],
            }
        ],
        "data_quality": _living_input()["data_quality"],
    }


def test_validate_living_market_report_accepts_valid_payload():
    validate_living_market_report(
        _valid_living_report(),
        input_payload=_living_input(),
        expected_version=1,
    )


def test_validate_living_market_report_rejects_banned_terms():
    report = _valid_living_report()
    report["executive_summary"] = "这个报告提到 赏金。"

    with pytest.raises(LivingMarketReportError, match="banned"):
        validate_living_market_report(report, input_payload=_living_input(), expected_version=1)


def test_validate_living_market_report_allows_open_source_language():
    report = _valid_living_report()
    report["sections"][0]["body"] = "open source AI infra 工具链仍是市场结构的一部分。"

    validate_living_market_report(report, input_payload=_living_input(), expected_version=1)


def test_validate_living_market_report_rejects_claim_without_evidence():
    report = _valid_living_report()
    report["claims"][0]["evidence_ids"] = []

    with pytest.raises(LivingMarketReportError, match="evidence"):
        validate_living_market_report(report, input_payload=_living_input(), expected_version=1)


def test_validate_living_market_report_rejects_unknown_evidence_id():
    report = _valid_living_report()
    report["claims"][0]["evidence_ids"] = ["missing"]

    with pytest.raises(LivingMarketReportError, match="evidence"):
        validate_living_market_report(report, input_payload=_living_input(), expected_version=1)


def test_validate_living_market_report_requires_previous_claim_for_non_new_status():
    report = _valid_living_report()
    report["claims"][0]["status"] = "reinforced"
    report["claims"][0]["previous_claim_id"] = None

    with pytest.raises(LivingMarketReportError, match="previous_claim_id"):
        validate_living_market_report(report, input_payload=_living_input(), expected_version=1)


def test_generate_living_market_report_payload_raises_after_invalid_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(market_intelligence_living_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages, **_kwargs):
        calls.append(messages)
        return "{invalid json"

    monkeypatch.setattr(market_intelligence_living_report, "request_structured_json", fake_request_structured_json)

    with pytest.raises(LivingMarketReportError, match="LLM report failed validation"):
        generate_living_market_report_payload(
            _living_input(),
            version=1,
            mode="baseline_seed",
            previous_snapshot_id=None,
            generated_at=datetime(2026, 4, 27, 10, 0, 0),
        )

    assert len(calls) == 2


def test_build_rule_living_market_report_passes_validation():
    report = build_rule_living_market_report(
        _living_input(),
        version=1,
        mode="baseline_seed",
        previous_snapshot_id=None,
        generated_at=datetime(2026, 4, 27, 10, 0, 0),
    )

    validate_living_market_report(report, input_payload=_living_input(), expected_version=1)
