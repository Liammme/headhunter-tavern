from datetime import datetime

from app.models import Job
from app.services.company_clue_letter import generate_company_clue_letter
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
            '因为它同时把高赏金 AI 岗和增长岗放出来，节奏不像普通补人，更像在补关键推进位。'
            '你抬眼示意他继续，他点了点 Principal AI Engineer，说这类岗位带着时间压力、业务关键性和持续招不动的味道，'
            '再配上可直接进官网与原帖的入口，足够先开一轮侦查。最后他只留一句：先顺着高赏金 AI 岗和官网入口去查团队真实需求。",'
            '"sections":['
            '{"key":"lead","title":"我先看到的","content":"OpenGradient 同时挂出高赏金 AI 岗和增长岗。"},'
            '{"key":"evidence","title":"这家公司现在露出的口子","content":"Principal AI Engineer 带时间压力与关键岗位信号，且已有官网与岗位原帖入口。"},'
            '{"key":"next_move","title":"你下一步怎么查","content":"先查官网，再回到高赏金岗位原帖核对团队扩张节奏。"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert result["company"] == "OpenGradient"
    assert result["generated_at"] == "2026-04-22T09:00:00"
    assert "James侦探" in result["narrative"]
    assert [section["key"] for section in result["sections"]] == ["lead", "evidence", "next_move"]


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

    captured_input: list[dict] = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_prompt(llm_input: dict) -> str:
        captured_input.append(llm_input)
        return "prompt"

    monkeypatch.setattr("app.services.company_clue_letter.build_company_clue_user_prompt", fake_prompt)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (
            '{"narrative":"James侦探说这家公司露出的线索够用了。",'
            '"sections":['
            '{"key":"lead","title":"我先看到的","content":"测试"},'
            '{"key":"evidence","title":"这家公司现在露出的口子","content":"测试"},'
            '{"key":"next_move","title":"你下一步怎么查","content":"测试"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert captured_input
    llm_input = captured_input[0]
    assert set(llm_input.keys()) == {"company_summary", "highlighted_jobs", "entry_points"}
    assert llm_input["company_summary"]["estimated_bounty"]["amount"] == 1500
    assert llm_input["highlighted_jobs"][0]["entry_points"]["company_url"] == "https://opengradient.ai"
    assert llm_input["highlighted_jobs"][0]["entry_points"]["hiring_page"] == "https://opengradient.ai/careers"
    assert llm_input["highlighted_jobs"][0]["entry_points"]["email"] == "careers@opengradient.ai"
    assert "description" not in llm_input["highlighted_jobs"][0]
    assert "description" not in llm_input["company_summary"]


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

    captured_input: list[dict] = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_prompt(llm_input: dict) -> str:
        captured_input.append(llm_input)
        return "prompt"

    monkeypatch.setattr("app.services.company_clue_letter.build_company_clue_user_prompt", fake_prompt)
    monkeypatch.setattr(
        "app.services.company_clue_letter.request_zhipu_structured_json",
        lambda messages: (
            '{"narrative":"James侦探说这家公司露出的线索够用了。",'
            '"sections":['
            '{"key":"lead","title":"我先看到的","content":"测试"},'
            '{"key":"evidence","title":"这家公司现在露出的口子","content":"测试"},'
            '{"key":"next_move","title":"你下一步怎么查","content":"测试"}'
            ']}'
        ),
    )

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert captured_input[0]["company_summary"]["estimated_bounty"] is None


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


def test_generate_company_clue_letter_returns_failure_when_llm_is_unavailable(db_session):
    db_session.add(build_job(company="OpenGradient", title="Principal AI Engineer", canonical_url="https://jobs.example.com/opengradient/1"))
    db_session.commit()

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
            {"key": "lead", "title": "我先看到的", "content": "测试内容"},
            {"key": "evidence", "title": "这家公司现在露出的口子", "content": "测试内容"},
            {"key": "next_move", "title": "你下一步怎么查", "content": "测试内容"},
        ],
        "error_message": None,
    }

    monkeypatch.setattr("app.api.company_clue.generate_company_clue_letter", lambda db, company: expected)

    response = client.post("/api/v1/company-clue", json={"company": "OpenGradient"})

    assert response.status_code == 200
    assert response.json() == expected
