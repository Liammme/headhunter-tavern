import pytest

from app.services import market_intelligence_report
from app.services.market_intelligence_report import (
    MarketIntelligenceReportError,
    build_market_intelligence_system_prompt,
    build_market_intelligence_user_prompt,
    build_rule_market_report,
    generate_market_report,
    parse_market_intelligence_report,
    validate_market_intelligence_report,
)


def _valid_report() -> dict:
    return {
        "headline": "AI infra demand is broadening",
        "narrative": "AI infra demand expanded across 30d and remains visible in the 90d window.",
        "primary_judgment": {
            "claim": "AI infra is moving from isolated platform teams into broader product groups.",
            "why_it_matters": "This points to durable investment rather than a short hiring spike.",
            "confidence": "medium",
        },
        "perspectives": [
            {
                "lens": "industry",
                "judgment": "Infrastructure hiring remains active across model deployment and data systems.",
                "evidence": ["AI infra appears in recent demand", "OpenGradient is represented"],
            },
            {
                "lens": "product_business",
                "judgment": "Teams are connecting infrastructure work to production product outcomes.",
                "evidence": ["Product-facing platform roles are present"],
            },
            {
                "lens": "organization_hiring",
                "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
                "evidence": ["Engineering ownership language is visible"],
            },
        ],
        "trend_cards": [
            {
                "title": "AI infra",
                "direction": "rising",
                "time_horizon": "30d",
                "judgment": "Demand is strengthening in platform and deployment work.",
                "evidence": ["AI infra", "OpenGradient"],
                "confidence": "medium",
            }
        ],
        "watchlist": ["AI infra", "OpenGradient"],
    }


def test_validate_market_intelligence_report_accepts_valid_payload():
    validate_market_intelligence_report(
        _valid_report(),
        allowed_terms={"AI infra", "OpenGradient"},
    )


def test_validate_market_intelligence_report_rejects_bounty_or_bd_language():
    report = _valid_report()
    report["narrative"] = "30d demand mentions BD and high bounty / 赏金 language."

    with pytest.raises(MarketIntelligenceReportError, match="banned"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_requires_all_perspectives():
    report = _valid_report()
    report["perspectives"] = report["perspectives"][:2]

    with pytest.raises(MarketIntelligenceReportError, match="perspectives"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_allows_extra_perspective_lens():
    report = _valid_report()
    report["perspectives"].append(
        {
            "lens": "capital_market",
            "judgment": "Funding context can be watched separately from hiring demand.",
            "evidence": ["30d signal"],
        }
    )

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_parse_market_intelligence_report_accepts_code_fence():
    content = """```json
{"headline": "AI infra", "narrative": "30d and 90d signal"}
```"""

    assert parse_market_intelligence_report(content) == {
        "headline": "AI infra",
        "narrative": "30d and 90d signal",
    }


def test_validate_market_intelligence_report_rejects_invalid_trend_card_enum():
    report = _valid_report()
    report["trend_cards"][0]["direction"] = "accelerating"

    with pytest.raises(MarketIntelligenceReportError, match="direction"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_more_than_four_trend_cards():
    report = _valid_report()
    report["trend_cards"] = report["trend_cards"] * 5

    with pytest.raises(MarketIntelligenceReportError, match="trend_cards"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_more_than_three_watchlist_items():
    report = _valid_report()
    report["watchlist"] = ["AI infra", "OpenGradient", "LLM serving", "RAG"]

    with pytest.raises(MarketIntelligenceReportError, match="watchlist"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_requires_30d_or_90d_in_narrative():
    report = _valid_report()
    report["narrative"] = "Recent demand remains visible across platform engineering."

    with pytest.raises(MarketIntelligenceReportError, match="30d|90d"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_build_market_intelligence_system_prompt_contains_quality_gate_instructions():
    prompt = build_market_intelligence_system_prompt()

    for phrase in ["BD", "猎头", "赏金", "认领", "客户开发", "岗位来源", "岗位链接"]:
        assert phrase in prompt
    assert "JSON" in prompt
    assert "30d" in prompt
    assert "90d" in prompt
    assert "primary judgment" in prompt


def test_build_market_intelligence_user_prompt_preserves_non_ascii_payload():
    prompt = build_market_intelligence_user_prompt({"主题": "AI 基础设施"})

    assert "主题" in prompt
    assert "AI 基础设施" in prompt
    assert "\\u4e3b\\u9898" not in prompt


def test_build_rule_market_report_passes_validation():
    report = build_rule_market_report({})

    validate_market_intelligence_report(report, allowed_terms=set())


def test_generate_market_report_returns_rule_fallback_when_llm_disabled(monkeypatch):
    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: False)

    report = generate_market_report({})

    validate_market_intelligence_report(report, allowed_terms=set())


def test_generate_market_report_uses_llm_payload_when_enabled(monkeypatch):
    expected = _valid_report()
    calls = []

    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages):
        calls.append(messages)
        return """```json
{
  "headline": "AI infra demand is broadening",
  "narrative": "AI infra demand expanded across 30d and remains visible in the 90d window.",
  "primary_judgment": {
    "claim": "AI infra is moving from isolated platform teams into broader product groups.",
    "why_it_matters": "This points to durable investment rather than a short hiring spike.",
    "confidence": "medium"
  },
  "perspectives": [
    {
      "lens": "industry",
      "judgment": "Infrastructure hiring remains active across model deployment and data systems.",
      "evidence": ["AI infra appears in recent demand", "OpenGradient is represented"]
    },
    {
      "lens": "product_business",
      "judgment": "Teams are connecting infrastructure work to production product outcomes.",
      "evidence": ["Product-facing platform roles are present"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
      "evidence": ["Engineering ownership language is visible"]
    }
  ],
  "trend_cards": [
    {
      "title": "AI infra",
      "direction": "rising",
      "time_horizon": "30d",
      "judgment": "Demand is strengthening in platform and deployment work.",
      "evidence": ["AI infra", "OpenGradient"],
      "confidence": "medium"
    }
  ],
  "watchlist": ["AI infra", "OpenGradient"]
}
```"""

    monkeypatch.setattr(
        market_intelligence_report,
        "request_structured_json",
        fake_request_structured_json,
    )

    report = generate_market_report({"theme": "AI infra"})

    assert report == expected
    assert calls
