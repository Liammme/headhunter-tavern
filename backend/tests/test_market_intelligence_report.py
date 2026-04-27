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
                "evidence": ["AI infra product-facing platform roles are present"],
            },
            {
                "lens": "organization_hiring",
                "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
                "evidence": ["OpenGradient engineering ownership language is visible"],
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


def test_validate_market_intelligence_report_rejects_bounty_language():
    report = _valid_report()
    report["narrative"] = "30d demand mentions high bounty / 赏金 language."

    with pytest.raises(MarketIntelligenceReportError, match="banned"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_allows_bd_when_it_is_a_market_role():
    report = _valid_report()
    report["narrative"] = "Recent Business Development and BD hiring is visible in go-to-market roles."
    report["perspectives"][2]["evidence"] = ["OpenGradient lists BD market roles"]

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_english_source_or_link_language():
    report = _valid_report()
    report["narrative"] = "30d narrative mentions source and link details."

    with pytest.raises(MarketIntelligenceReportError, match="banned"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_english_bounty_claim_terms():
    cases = [
        ("narrative", "30d demand describes a high bounty."),
        ("headline", "Customer claim pressure is rising"),
        ("watchlist", ["claimed roles"]),
    ]

    for field, value in cases:
        report = _valid_report()
        report[field] = value

        with pytest.raises(MarketIntelligenceReportError, match="banned"):
            validate_market_intelligence_report(
                report,
                allowed_terms={"AI infra", "OpenGradient"},
            )


def test_validate_market_intelligence_report_rejects_hyphenated_banned_terms_everywhere():
    for term in [
        "bounty-grade",
        "claim-status",
        "claimed-role",
        "source-led",
        "link-based",
        "customer-claim",
    ]:
        for field in ["narrative", "evidence", "watchlist"]:
            report = _valid_report()
            if field == "narrative":
                report["narrative"] = f"30d demand contains {term} phrasing."
            elif field == "evidence":
                report["perspectives"][0]["evidence"] = [f"OpenGradient mentions {term}"]
            else:
                report["watchlist"] = [term]

            with pytest.raises(MarketIntelligenceReportError, match="banned"):
                validate_market_intelligence_report(
                    report,
                    allowed_terms={"AI infra", "OpenGradient"},
                )


def test_validate_market_intelligence_report_allows_hyphenated_bd_role_language():
    report = _valid_report()
    report["narrative"] = "Recent demand includes BD-focused market roles."
    report["trend_cards"][0]["evidence"] = ["OpenGradient has BD-focused roles"]

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_allows_non_leakage_source_or_link_words():
    report = _valid_report()
    report["narrative"] = (
        "30d resource planning mentions open-source tooling, LinkedIn visibility, "
        "and reclaimed capacity."
    )

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_job_link_language():
    report = _valid_report()
    report["narrative"] = "30d narrative mentions 岗位链接."

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
            "evidence": ["AI infra 30d signal"],
        }
    )

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_unanchored_evidence():
    report = _valid_report()
    report["perspectives"][0]["evidence"] = ["UnknownCorp expanded hiring"]

    with pytest.raises(MarketIntelligenceReportError, match="evidence"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_empty_perspective_evidence():
    report = _valid_report()
    report["perspectives"][0]["evidence"] = []

    with pytest.raises(MarketIntelligenceReportError, match="evidence"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_empty_trend_evidence():
    report = _valid_report()
    report["trend_cards"][0]["evidence"] = []

    with pytest.raises(MarketIntelligenceReportError, match="evidence"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_empty_trend_cards():
    report = _valid_report()
    report["trend_cards"] = []

    with pytest.raises(MarketIntelligenceReportError, match="trend_cards"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_uses_boundaries_for_short_ascii_terms():
    for evidence in ["plain signal", "ongoing hiring", "throughput hiring"]:
        report = _valid_report()
        report["perspectives"][0]["evidence"] = [evidence]

        with pytest.raises(MarketIntelligenceReportError, match="evidence"):
            validate_market_intelligence_report(report, allowed_terms={"AI", "Go", "HR"})

    for evidence in ["AI signal", "Go hiring", "HR hiring"]:
        report = _valid_report()
        for perspective in report["perspectives"]:
            perspective["evidence"] = [evidence]
        report["trend_cards"][0]["evidence"] = [evidence]

        validate_market_intelligence_report(report, allowed_terms={"AI", "Go", "HR"})


def test_validate_market_intelligence_report_matches_slash_spaced_terms():
    report = _valid_report()
    for perspective in report["perspectives"]:
        perspective["evidence"] = ["Agent/RAG主题在90天内计14个岗位"]
    report["trend_cards"][0]["evidence"] = ["Agent/RAG主题在90天内计14个岗位"]

    validate_market_intelligence_report(report, allowed_terms={"agent / RAG"})


def test_generate_market_report_accepts_chinese_theme_alias_evidence(monkeypatch):
    expected = _valid_report()
    expected["narrative"] = "Recent demand remains visible across platform engineering."
    expected["perspectives"][0]["evidence"] = ["开发者工具主题在30天窗口内计13个岗位"]
    expected["trend_cards"][0]["evidence"] = ["开发者工具主题在30天窗口内计13个岗位"]
    calls = []

    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages):
        calls.append(messages)
        return """```json
{
  "headline": "AI infra demand is broadening",
  "narrative": "Recent demand remains visible across platform engineering.",
  "primary_judgment": {
    "claim": "AI infra is moving from isolated platform teams into broader product groups.",
    "why_it_matters": "This points to durable investment rather than a short hiring spike.",
    "confidence": "medium"
  },
  "perspectives": [
    {
      "lens": "industry",
      "judgment": "Infrastructure hiring remains active across model deployment and data systems.",
      "evidence": ["开发者工具主题在30天窗口内计13个岗位"]
    },
    {
      "lens": "product_business",
      "judgment": "Teams are connecting infrastructure work to production product outcomes.",
      "evidence": ["AI infra product-facing platform roles are present"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
      "evidence": ["OpenGradient engineering ownership language is visible"]
    }
  ],
  "trend_cards": [
    {
      "title": "AI infra",
      "direction": "rising",
      "time_horizon": "30d",
      "judgment": "Demand is strengthening in platform and deployment work.",
      "evidence": ["开发者工具主题在30天窗口内计13个岗位"],
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

    report = generate_market_report(
        {
            "windows": {
                "30d": {
                    "theme_counts": {"developer tools": 13},
                    "function_counts": {"技术": 34},
                }
            },
            "representative_samples": [
                {
                    "company": "OpenGradient",
                    "title": "AI Infrastructure Engineer",
                    "domain": "AI infra",
                }
            ],
        }
    )

    assert report == expected
    assert calls


def test_generate_market_report_accepts_title_alias_and_seniority_evidence(monkeypatch):
    expected = _valid_report()
    expected["narrative"] = "Recent demand remains visible across platform engineering."
    expected["perspectives"][0]["evidence"] = ["代表样本中多数为Mid级别，仅一个Senior标题"]
    expected["trend_cards"][0]["evidence"] = ["'SPDK Software Expert'"]
    calls = []

    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages):
        calls.append(messages)
        return """```json
{
  "headline": "AI infra demand is broadening",
  "narrative": "Recent demand remains visible across platform engineering.",
  "primary_judgment": {
    "claim": "AI infra is moving from isolated platform teams into broader product groups.",
    "why_it_matters": "This points to durable investment rather than a short hiring spike.",
    "confidence": "medium"
  },
  "perspectives": [
    {
      "lens": "industry",
      "judgment": "Infrastructure hiring remains active across model deployment and data systems.",
      "evidence": ["代表样本中多数为Mid级别，仅一个Senior标题"]
    },
    {
      "lens": "product_business",
      "judgment": "Teams are connecting infrastructure work to production product outcomes.",
      "evidence": ["AI infra product-facing platform roles are present"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
      "evidence": ["OpenGradient engineering ownership language is visible"]
    }
  ],
  "trend_cards": [
    {
      "title": "AI infra",
      "direction": "rising",
      "time_horizon": "30d",
      "judgment": "Demand is strengthening in platform and deployment work.",
      "evidence": ["'SPDK Software Expert'"],
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

    report = generate_market_report(
        {
            "windows": {
                "30d": {
                    "theme_counts": {"AI infra": 35},
                    "function_counts": {"技术": 34},
                }
            },
            "representative_samples": [
                {
                    "company": "OpenGradient",
                    "title": "SPDK Software Expert – Next-Generation AI Infrastructure Storage Platform",
                    "domain": "AI infra",
                    "seniority": "Senior",
                },
                {
                    "company": None,
                    "title": "[BD] AI Software QA (Next-Gen & AI-Driven Testing) - 6 months Internship",
                    "domain": "other",
                    "seniority": "Mid",
                },
            ],
        }
    )

    assert report == expected
    assert calls


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


def test_validate_market_intelligence_report_accepts_long_horizon_in_trend_cards_without_narrative_token():
    report = _valid_report()
    report["narrative"] = "Recent demand remains visible across platform engineering."

    validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_requires_long_horizon_trend_card():
    report = _valid_report()
    report["trend_cards"][0]["time_horizon"] = "7d"

    with pytest.raises(MarketIntelligenceReportError, match="30d|90d"):
        validate_market_intelligence_report(report, allowed_terms={"AI infra", "OpenGradient"})


def test_build_market_intelligence_system_prompt_contains_quality_gate_instructions():
    prompt = build_market_intelligence_system_prompt()

    for phrase in ["猎头", "赏金", "认领", "客户开发", "岗位来源", "岗位链接"]:
        assert phrase in prompt
    assert "Never mention BD" not in prompt
    assert "BD" in prompt
    assert "Business Development" in prompt
    for field in [
        "headline",
        "narrative",
        "primary_judgment",
        "perspectives",
        "trend_cards",
        "watchlist",
        "confidence",
        "direction",
        "time_horizon",
    ]:
        assert field in prompt
    assert "JSON" in prompt
    assert "30d" in prompt
    assert "90d" in prompt
    assert "primary judgment" in prompt
    for lens in ["industry", "product_business", "organization_hiring"]:
        assert lens in prompt
    for enum_value in ["rising", "cooling", "shifting", "stable", "emerging"]:
        assert enum_value in prompt
    assert "watchlist max 3" in prompt
    assert "trend cards max 4" in prompt
    assert "representative sample company when present/title/domain" in prompt
    assert "Do not describe a job board or source site as a company" in prompt
    assert "Every evidence item" in prompt
    assert "Do not write generic evidence" in prompt
    assert '"primary_judgment": {' in prompt
    assert '"claim":' in prompt
    assert '"why_it_matters":' in prompt
    assert '"perspectives": [' in prompt
    assert '"trend_cards": [' in prompt
    assert '"title":' in prompt
    assert '"judgment":' in prompt
    assert '"evidence":' in prompt


def test_build_market_intelligence_user_prompt_preserves_non_ascii_payload():
    prompt = build_market_intelligence_user_prompt({"主题": "AI 基础设施"})

    assert "主题" in prompt
    assert "AI 基础设施" in prompt
    assert "\\u4e3b\\u9898" not in prompt


def test_build_rule_market_report_passes_validation():
    report = build_rule_market_report({})

    validate_market_intelligence_report(report, allowed_terms=set())


def test_build_rule_market_report_uses_chinese_market_language():
    report = build_rule_market_report({})

    assert "市场" in report["headline"]
    assert "需求" in report["narrative"]
    assert "bounty" not in str(report).lower()
    assert "赏金" not in str(report)


def test_generate_market_report_returns_rule_fallback_when_llm_disabled(monkeypatch):
    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: False)

    report = generate_market_report({})

    validate_market_intelligence_report(report, allowed_terms=set())


def test_generate_market_report_returns_rule_fallback_when_llm_has_no_anchors(monkeypatch):
    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages):
        raise AssertionError("LLM should not be called without representative sample anchors")

    monkeypatch.setattr(
        market_intelligence_report,
        "request_structured_json",
        fake_request_structured_json,
    )

    report = generate_market_report({"representative_samples": []})

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
      "evidence": ["AI infra product-facing platform roles are present"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
      "evidence": ["OpenGradient engineering ownership language is visible"]
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

    report = generate_market_report(
        {
            "representative_samples": [
                {
                    "company": "OpenGradient",
                    "title": "AI Infrastructure Engineer",
                    "domain": "AI infra",
                }
            ]
        }
    )

    assert report == expected
    assert calls


def test_generate_market_report_accepts_aggregate_window_evidence(monkeypatch):
    expected = _valid_report()
    expected["narrative"] = "Recent demand remains visible across platform engineering."
    expected["perspectives"][0]["evidence"] = ["技术类在30d窗口占34个岗位"]
    expected["trend_cards"][0]["evidence"] = ["技术类在30d窗口占34个岗位"]
    calls = []

    monkeypatch.setattr(market_intelligence_report, "should_use_llm", lambda: True)

    def fake_request_structured_json(messages):
        calls.append(messages)
        return """```json
{
  "headline": "AI infra demand is broadening",
  "narrative": "Recent demand remains visible across platform engineering.",
  "primary_judgment": {
    "claim": "AI infra is moving from isolated platform teams into broader product groups.",
    "why_it_matters": "This points to durable investment rather than a short hiring spike.",
    "confidence": "medium"
  },
  "perspectives": [
    {
      "lens": "industry",
      "judgment": "Infrastructure hiring remains active across model deployment and data systems.",
      "evidence": ["技术类在30d窗口占34个岗位"]
    },
    {
      "lens": "product_business",
      "judgment": "Teams are connecting infrastructure work to production product outcomes.",
      "evidence": ["AI infra product-facing platform roles are present"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "Hiring suggests practical buildout rather than pure research expansion.",
      "evidence": ["OpenGradient engineering ownership language is visible"]
    }
  ],
  "trend_cards": [
    {
      "title": "AI infra",
      "direction": "rising",
      "time_horizon": "30d",
      "judgment": "Demand is strengthening in platform and deployment work.",
      "evidence": ["技术类在30d窗口占34个岗位"],
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

    report = generate_market_report(
        {
            "windows": {
                "30d": {
                    "theme_counts": {"AI infra": 35},
                    "function_counts": {"技术": 34},
                }
            },
            "representative_samples": [
                {
                    "company": "OpenGradient",
                    "title": "AI Infrastructure Engineer",
                    "domain": "AI infra",
                }
            ],
        }
    )

    assert report == expected
    assert calls
