from datetime import datetime

from app.models import Job
from app.services.company_clue_letter import generate_company_clue_letter


def build_job(*, company: str, title: str, canonical_url: str, bounty_grade: str = "high") -> Job:
    return Job(
        canonical_url=canonical_url,
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description="test",
        posted_at=datetime(2026, 4, 22, 9, 0, 0),
        collected_at=datetime(2026, 4, 22, 9, 0, 0),
        bounty_grade=bounty_grade,
        signal_tags={"display_tags": ["AI"], "company_url": f"https://companies.example.com/{company.lower()}"},
    )


def test_generate_company_clue_letter_returns_success_contract(db_session):
    db_session.add_all(
        [
            build_job(
                company="OpenGradient",
                title="Principal AI Engineer",
                canonical_url="https://jobs.example.com/opengradient/1",
                bounty_grade="high",
            ),
            build_job(
                company="OpenGradient",
                title="Growth Engineer",
                canonical_url="https://jobs.example.com/opengradient/2",
                bounty_grade="medium",
            ),
        ]
    )
    db_session.commit()

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert result["company"] == "OpenGradient"
    assert result["generated_at"] == "2026-04-22T09:00:00"
    assert result["narrative"]
    assert [section["key"] for section in result["sections"]] == [
        "what_i_saw",
        "what_it_means",
        "next_move",
    ]


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
        "narrative": "单公司线索来信契约已建立，真实生成将在下一阶段接入。",
        "sections": [
            {"key": "what_i_saw", "title": "我先看到的", "content": "测试内容"},
            {"key": "what_it_means", "title": "这说明什么", "content": "测试内容"},
            {"key": "next_move", "title": "你下一步怎么动", "content": "测试内容"},
        ],
        "error_message": None,
    }

    monkeypatch.setattr("app.api.company_clue.generate_company_clue_letter", lambda db, company: expected)

    response = client.post("/api/v1/company-clue", json={"company": "OpenGradient"})

    assert response.status_code == 200
    assert response.json() == expected
