from datetime import date, datetime

from app.models import CompanyDailySummary, IntelligenceSnapshot
from app.services.home_snapshot_read_service import load_home_snapshot_candidate


def test_load_home_snapshot_candidate_reads_daily_summaries_and_latest_intelligence(db_session):
    db_session.add_all(
        [
            CompanyDailySummary(
                summary_date=date(2026, 4, 18),
                company_normalized="opengradient",
                company_display_name="OpenGradient",
                company_grade="focus",
                job_count=2,
                representative_job_ids=[1, 2],
                claimed_names=["Mina"],
            ),
            CompanyDailySummary(
                summary_date=date(2026, 4, 18),
                company_normalized="beta-labs",
                company_display_name="Beta Labs",
                company_grade="normal",
                job_count=1,
                representative_job_ids=[3],
                claimed_names=[],
            ),
            IntelligenceSnapshot(
                snapshot_payload={
                    "headline": "James侦探说今天先盯 OpenGradient。",
                    "summary": "今天 OpenGradient 有新增高赏金 AI 岗位。",
                    "narrative": "James侦探说今天先盯 OpenGradient。你抬眼示意他继续，他说变化来自新增高赏金 AI 岗位。",
                    "findings": ["OpenGradient 今天新增核心岗。"],
                    "actions": ["先看 OpenGradient 的 AI 岗。"],
                    "analysis_version": "feed-v1",
                    "rule_version": "score-v2",
                    "window_start": "2026-04-05",
                    "window_end": "2026-04-18",
                    "generated_at": "2026-04-18T10:00:00",
                },
                generated_at=datetime(2026, 4, 18, 10, 0, 0),
            ),
        ]
    )
    db_session.commit()

    candidate = load_home_snapshot_candidate(db_session, snapshot_date=date(2026, 4, 18))

    assert candidate["snapshot_date"] == "2026-04-18"
    assert candidate["ready_for_home"] is False
    assert any("CompanyDailySummary 缺少岗位卡完整字段" in reason for reason in candidate["blocking_reasons"])
    assert candidate["company_summaries"] == [
        {
            "company": "OpenGradient",
            "company_normalized": "opengradient",
            "company_grade": "focus",
            "job_count": 2,
            "representative_job_ids": [1, 2],
            "claimed_names": ["Mina"],
        },
        {
            "company": "Beta Labs",
            "company_normalized": "beta-labs",
            "company_grade": "normal",
            "job_count": 1,
            "representative_job_ids": [3],
            "claimed_names": [],
        },
    ]
    assert candidate["intelligence"]["headline"] == "James侦探说今天先盯 OpenGradient。"
    assert "days" not in candidate
    assert "meta" not in candidate


def test_load_home_snapshot_candidate_reports_missing_snapshot_parts(db_session):
    candidate = load_home_snapshot_candidate(db_session, snapshot_date=date(2026, 4, 18))

    assert candidate == {
        "snapshot_date": "2026-04-18",
        "ready_for_home": False,
        "blocking_reasons": [
            "缺少 CompanyDailySummary 日级公司快照。",
            "缺少 IntelligenceSnapshot 情报快照。",
            "CompanyDailySummary 缺少岗位卡完整字段，不能直接替代 /api/v1/home。",
        ],
        "company_summaries": [],
        "intelligence": None,
    }


def test_load_home_snapshot_candidate_filters_company_summaries_by_date(db_session):
    db_session.add_all(
        [
            CompanyDailySummary(
                summary_date=date(2026, 4, 17),
                company_normalized="oldco",
                company_display_name="Old Co",
                company_grade="focus",
                job_count=9,
                representative_job_ids=[9],
                claimed_names=[],
            ),
            CompanyDailySummary(
                summary_date=date(2026, 4, 18),
                company_normalized="opengradient",
                company_display_name="OpenGradient",
                company_grade="focus",
                job_count=1,
                representative_job_ids=[1],
                claimed_names=[],
            ),
        ]
    )
    db_session.commit()

    candidate = load_home_snapshot_candidate(db_session, snapshot_date=date(2026, 4, 18))

    assert [item["company"] for item in candidate["company_summaries"]] == ["OpenGradient"]


def test_load_home_snapshot_candidate_uses_latest_intelligence_snapshot(db_session):
    db_session.add_all(
        [
            IntelligenceSnapshot(
                snapshot_payload={"headline": "old"},
                generated_at=datetime(2026, 4, 18, 9, 0, 0),
            ),
            IntelligenceSnapshot(
                snapshot_payload={"headline": "new"},
                generated_at=datetime(2026, 4, 18, 10, 0, 0),
            ),
        ]
    )
    db_session.commit()

    candidate = load_home_snapshot_candidate(db_session, snapshot_date=date(2026, 4, 18))

    assert candidate["intelligence"] == {"headline": "new"}


def test_home_endpoint_does_not_expose_snapshot_candidate_fields(client):
    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert "ready_for_home" not in body
    assert "blocking_reasons" not in body
    assert "company_summaries" not in body
