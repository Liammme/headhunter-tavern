from datetime import datetime, timedelta

from app.core.config import settings
from app.models import Job
from app.services.company_clue_context import build_company_clue_context
from app.services.company_clue_letter import generate_company_clue_letter, _should_use_company_clue_llm
from app.services.intelligence import IntelligenceGenerationError


def build_job(
    *,
    company: str,
    title: str,
    canonical_url: str,
    bounty_grade: str = "high",
    description: str = "test",
    signal_tags: dict | None = None,
) -> Job:
    return Job(
        canonical_url=canonical_url,
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=datetime(2026, 4, 22, 9, 0, 0),
        collected_at=datetime(2026, 4, 22, 9, 0, 0),
        bounty_grade=bounty_grade,
        signal_tags=signal_tags
        or {
            "display_tags": ["AI"],
            "company_url": f"https://companies.example.com/{company.lower()}",
        },
    )


def build_windowed_job(*, company: str, title: str, days_ago: int) -> Job:
    current = datetime(2026, 4, 23, 12, 0, 0) - timedelta(days=days_ago)
    return Job(
        canonical_url=f"https://jobs.example.com/{company.lower()}/{title.lower().replace(' ', '-')}",
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=f"{title} urgent hiring now",
        posted_at=current,
        collected_at=current,
        bounty_grade="high",
        signal_tags={
            "display_tags": ["AI"],
            "company_url": f"https://{company.lower()}.example.com",
        },
    )


def test_company_clue_llm_availability_accepts_generic_llm_key(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", None)
    monkeypatch.setattr(settings, "bounty_pool_llm_api_key", "generic-key")

    assert _should_use_company_clue_llm() is True


def test_generate_company_clue_letter_returns_success_contract(db_session, monkeypatch):
    db_session.add_all(
        [
            build_job(
                company="OpenGradient",
                title="Principal AI Engineer",
                canonical_url="https://jobs.example.com/opengradient/1",
                bounty_grade="high",
                description="urgent llm infra founding role careers@opengradient.ai",
                signal_tags={
                    "display_tags": ["AI"],
                    "company_url": "https://opengradient.ai",
                    "estimated_bounty_amount": 1500,
                    "estimated_bounty_label": "¥1,500",
                    "estimated_bounty_min": 1200,
                    "estimated_bounty_max": 1800,
                    "estimated_bounty_rate_pct": 12,
                    "estimated_bounty_rule_version": "bounty-rule-v1",
                    "estimated_bounty_confidence": "medium",
                },
            ),
            build_job(
                company="OpenGradient",
                title="Growth Engineer",
                canonical_url="https://jobs.example.com/opengradient/2",
                bounty_grade="medium",
                description="growth roadmap customer delivery",
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (
            '{"narrative":"James侦探把名单往你面前一压，说 OpenGradient 这家公司值得先查，'
            '因为它同时把 Principal AI Engineer 和 Growth Engineer 放出来，节奏不像普通补人，更像在补关键推进位。'
            '你抬眼示意他继续，他点了点 Principal AI Engineer，说这类岗位带着时间压力、业务关键性和持续招不动的味道，'
            '再配上可直接进官网与原帖的入口，足够先开一轮侦查。最后他只留一句：先顺着高赏金 AI 岗和官网入口去查团队真实需求。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"OpenGradient 同时挂出 Principal AI Engineer 和 Growth Engineer。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 带时间压力与关键岗位信号，Growth Engineer 指向增长推进。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先查 https://opengradient.ai，再回到 https://jobs.example.com/opengradient/1 核对团队扩张节奏。"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert result["company"] == "OpenGradient"
    assert result["generated_at"] == "2026-04-22T09:00:00"
    assert "James侦探" in result["narrative"]
    assert [section["key"] for section in result["sections"]] == ["clue_1", "clue_2", "clue_3"]


def test_generate_company_clue_letter_rewrites_generic_first_pass_and_uses_windowed_jobs(db_session, monkeypatch):
    db_session.add(build_windowed_job(company="OpenGradient", title="Principal AI Engineer", days_ago=1))
    db_session.add(build_windowed_job(company="OpenGradient", title="Old Role", days_ago=30))
    db_session.commit()

    calls = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_request(messages):
        calls.append(messages)
        if len(calls) == 1:
            return (
                '{"narrative":"OpenGradient 表现突出，值得优先关注。",'
                '"sections":['
                '{"key":"lead","title":"为什么现在值得查","content":"值得优先关注。"},'
                '{"key":"evidence","title":"最能代表需求的岗位","content":"岗位比较关键。"},'
                '{"key":"next_move","title":"你下一步先验证什么","content":"建议持续观察。"}'
                ']}'
            )
        return (
            '{"narrative":"你现在先查 OpenGradient，因为 Principal AI Engineer 还在 14 天窗口里持续开放，说明它仍在补关键技术推进位。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 仍在当前窗口里开放，说明需求还在持续。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 这类岗位直接对应核心技术推进，不是普通补位。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先回到 https://jobs.example.com/opengradient/principal-ai-engineer 核对职责，再看 https://opengradient.example.com 是否还有相邻岗位。"}'
            ']}'
        )

    monkeypatch.setattr("app.services.company_clue_letter.request_zhipu_structured_json", fake_request)

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert len(calls) == 2
    assert "Principal AI Engineer" in result["narrative"]
    assert "Old Role" not in str(calls[-1])


def test_generate_company_clue_letter_uses_exact_company_match(db_session, monkeypatch):
    db_session.add(build_job(company="OpenGradient Labs", title="Staff Engineer", canonical_url="https://jobs.example.com/labs/1"))
    db_session.commit()

    llm_calls: list[object] = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: llm_calls.append(messages),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "failure"
    assert result["error_message"] == "Company not found"
    assert llm_calls == []


def test_generate_company_clue_letter_passes_structured_context_only(db_session, monkeypatch):
    db_session.add(
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            canonical_url="https://jobs.example.com/opengradient/1",
            bounty_grade="high",
            description="urgent llm infra platform roadmap hiring fast careers@opengradient.ai",
            signal_tags={
                "display_tags": ["AI"],
                "company_url": "https://opengradient.ai",
                "apply_url": "https://opengradient.ai/careers",
                "estimated_bounty_amount": 1500,
                "estimated_bounty_label": "¥1,500",
                "estimated_bounty_min": 1200,
                "estimated_bounty_max": 1800,
                "estimated_bounty_rate_pct": 12,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        )
    )
    db_session.commit()

    captured_context: list[dict] = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_messages(context: dict) -> list[dict]:
        captured_context.append(context)
        return [{"role": "user", "content": "prompt"}]

    monkeypatch.setattr("app.services.company_clue_letter.build_company_clue_messages", fake_messages)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (
            '{"narrative":"James侦探说 Principal AI Engineer 这条线索够用了。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 还在窗口内。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 是可验证岗位。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先查 https://jobs.example.com/opengradient/1。"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert captured_context
    llm_input = captured_context[0]
    assert set(llm_input.keys()) == {"company", "window", "summary", "role_clusters", "evidence_cards", "entry_points"}
    assert llm_input["window"]["window_days"] == 14
    assert llm_input["summary"]["estimated_bounty"]["amount"] == 1500
    assert llm_input["evidence_cards"][0]["entry_points"]["company_url"] == "https://opengradient.ai"
    assert llm_input["evidence_cards"][0]["entry_points"]["hiring_page"] == "https://opengradient.ai/careers"
    assert llm_input["evidence_cards"][0]["entry_points"]["email"] == "careers@opengradient.ai"
    assert "description" not in llm_input["evidence_cards"][0]
    assert "description" not in llm_input["summary"]


def test_build_company_clue_context_uses_first_complete_estimate_in_summary():
    jobs = [
        build_job(
            company="OpenGradient",
            title="Operations Coordinator",
            canonical_url="https://jobs.example.com/opengradient/ops",
            bounty_grade="low",
            description="operations support",
            signal_tags={
                "display_tags": ["运营"],
                "company_url": "https://opengradient.ai",
                "estimated_bounty_amount": 24000,
                "estimated_bounty_label": "¥19,200-¥28,800",
                "estimated_bounty_min": 19200,
                "estimated_bounty_max": 28800,
                "estimated_bounty_rate_pct": 12,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        ),
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            canonical_url="https://jobs.example.com/opengradient/principal-ai",
            bounty_grade="high",
            description="urgent llm infra platform roadmap hiring fast",
            signal_tags={
                "display_tags": ["AI"],
                "company_url": "https://opengradient.ai",
                "estimated_bounty_amount": 150000,
                "estimated_bounty_label": "¥120,000-¥180,000",
                "estimated_bounty_min": 120000,
                "estimated_bounty_max": 180000,
                "estimated_bounty_rate_pct": 20,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        ),
    ]

    llm_input = build_company_clue_context(company="OpenGradient", jobs=jobs, today=datetime(2026, 4, 23).date())

    assert llm_input["summary"]["estimated_bounty"]["amount"] == 24000
    assert llm_input["summary"]["estimated_bounty"]["label"] == "¥19,200-¥28,800"


def test_generate_company_clue_letter_ignores_partial_estimate_snapshot(db_session, monkeypatch):
    db_session.add(
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            canonical_url="https://jobs.example.com/opengradient/1",
            bounty_grade="high",
            description="urgent llm infra platform roadmap hiring fast careers@opengradient.ai",
            signal_tags={
                "display_tags": ["AI"],
                "company_url": "https://opengradient.ai",
                "estimated_bounty_amount": 1500,
                "estimated_bounty_label": "¥1,500",
            },
        )
    )
    db_session.commit()

    captured_context: list[dict] = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_messages(context: dict) -> list[dict]:
        captured_context.append(context)
        return [{"role": "user", "content": "prompt"}]

    monkeypatch.setattr("app.services.company_clue_letter.build_company_clue_messages", fake_messages)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (
            '{"narrative":"James侦探说 Principal AI Engineer 这条线索够用了。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 还在窗口内。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 是可验证岗位。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先查 https://jobs.example.com/opengradient/1。"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert captured_context[0]["summary"]["estimated_bounty"] is None


def test_generate_company_clue_letter_returns_failure_when_llm_generation_fails(db_session, monkeypatch):
    db_session.add(build_job(company="OpenGradient", title="Principal AI Engineer", canonical_url="https://jobs.example.com/opengradient/1"))
    db_session.commit()

    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (_ for _ in ()).throw(IntelligenceGenerationError("boom")),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "failure"
    assert result["company"] == "OpenGradient"
    assert result["sections"] == []
    assert result["error_message"] == "Company clue generation failed"
    assert "失败" in result["narrative"]


def test_generate_company_clue_letter_does_not_rewrite_internal_parser_errors(db_session, monkeypatch):
    db_session.add(build_job(company="OpenGradient", title="Principal AI Engineer", canonical_url="https://jobs.example.com/opengradient/1"))
    db_session.commit()

    calls = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: calls.append(messages)
        or (
            '{"narrative":"Principal AI Engineer 这条线索可查。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 还在窗口内。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 是可验证岗位。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先查 https://jobs.example.com/opengradient/1。"}'
            ']}'
        ),
    )
    monkeypatch.setattr(
        "app.services.company_clue_letter.parse_company_clue_response",
        lambda content: (_ for _ in ()).throw(RuntimeError("parser bug")),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "failure"
    assert result["error_message"] == "Company clue generation failed"
    assert len(calls) == 1


def test_generate_company_clue_letter_returns_failure_when_llm_is_unavailable(db_session, monkeypatch):
    db_session.add(build_job(company="OpenGradient", title="Principal AI Engineer", canonical_url="https://jobs.example.com/opengradient/1"))
    db_session.commit()
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: False)

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "failure"
    assert result["sections"] == []
    assert result["error_message"] == "Company clue generation unavailable"


def test_generate_company_clue_letter_returns_failure_contract_when_company_missing(db_session):
    result = generate_company_clue_letter(db_session, company="Missing Co")

    assert result["status"] == "failure"
    assert result["company"] == "Missing Co"
    assert result["generated_at"]
    assert result["narrative"]
    assert result["sections"] == []
    assert result["error_message"] == "Company not found"


def test_company_clue_endpoint_requires_company(client):
    response = client.post("/api/v1/company-clue", json={"company": ""})

    assert response.status_code == 422


def test_company_clue_endpoint_returns_service_contract(client, monkeypatch):
    expected = {
        "status": "success",
        "company": "OpenGradient",
        "generated_at": "2026-04-22T09:00:00",
        "narrative": "James侦探留下了一封单公司线索来信。",
        "sections": [
            {"key": "clue_1", "title": "线索一：露出的口子", "content": "测试内容"},
            {"key": "clue_2", "title": "线索二：卡住的岗位", "content": "测试内容"},
            {"key": "clue_3", "title": "线索三：下手路径", "content": "测试内容"},
        ],
        "error_message": None,
    }

    monkeypatch.setattr("app.api.company_clue.generate_company_clue_letter", lambda db, company: expected)

    response = client.post("/api/v1/company-clue", json={"company": "OpenGradient"})

    assert response.status_code == 200
    assert response.json() == expected
