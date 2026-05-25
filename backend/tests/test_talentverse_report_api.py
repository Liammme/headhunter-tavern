from datetime import datetime, timedelta

from app.models import TalentverseReport


def _payload() -> dict:
    return {
        "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        "subtitle": "基于 Talent Signal 公开招聘信号样本生成的 Talentverse 前沿科技招聘市场观察",
        "executiveSummary": "过去 180 天的公开招聘信号显示，全球招聘活动出现短期收缩。",
        "keySignals": [
            {
                "signal": "全球招聘活动短期收缩",
                "data": "近 7 天岗位数较 30 天下降 67.1%。",
                "interpretation": "企业更谨慎。",
                "hiringImplication": "关键岗位优先。",
                "confidence": "high",
                "evidenceRefs": ["fact-1561"],
            }
        ],
        "marketStructure": {"body": "AI 与数据岗位仍是核心。", "metrics": []},
        "demandShift": {"body": "短期收缩。", "metrics": []},
        "talentStrategyImplications": [{"title": "关键岗位优先", "body": "先判断岗位影响。"}],
        "risksAndWatchlist": [{"topic": "数据岗位", "reason": "观察是否继续扩张。", "evidenceRefs": ["fact-1561"]}],
        "talentverseView": "市场从数量扩张转向高确定性招聘。",
        "methodologyNote": {"sampleCount": 1189, "windowDays": 180, "body": "基于公开招聘信号。"},
        "faq": [{"question": "意味着什么？", "answer": "关注关键岗位。"}],
        "glossaryTerms": [{"term": "高确定性招聘", "definition": "关注岗位影响和证据质量。"}],
        "evidenceRefs": [{"id": "fact-1561", "note": "sample", "confidence": "high"}],
        "source": {"name": "Talent Signal", "url": "https://talentsignal.cloud"},
        "seo": {"title": "全球招聘活动短期收缩", "description": "Talentverse 报告。", "keywords": ["AI"]},
        "article": {
            "lead": "过去 180 天的公开招聘信号显示，全球招聘活动正在从广泛扩张转向更谨慎的关键岗位筛选。",
            "sections": [
                {"heading": "市场发生了什么", "body": "近 7 天岗位数较 30 天下降 67.1%，但关键技术岗位仍保持结构性需求。"},
                {"heading": "Talentverse 如何判断", "body": "Talentverse 将这轮变化理解为高确定性关键岗位招聘。"},
                {"heading": "这对关键岗位招聘意味着什么", "body": "AI、Web3、Fintech、Quant 与新经济团队需要重新排序关键岗位。"},
                {"heading": "企业应该如何调整", "body": "企业应先明确真正影响业务结果的关键岗位，再判断候选人证据链。"},
            ],
            "closing": "这轮招聘收缩意味着判断标准正在变高。",
        },
        "category": "market-intelligence",
        "tags": ["global"],
    }


def _add_report(
    db_session,
    *,
    slug: str,
    version: int,
    status: str = "published",
    updated_at: datetime | None = None,
) -> TalentverseReport:
    now = updated_at or datetime(2026, 5, 25, 10, 30, 0)
    report = TalentverseReport(
        raw_report_id=version,
        slug=slug,
        region="global",
        locale="zh-CN",
        title="全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        status=status,
        published_at=now if status == "published" else None,
        updated_at=now,
        version=version,
        payload=_payload(),
        created_at=now,
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    report.payload = {**report.payload, "id": f"tv-report-{report.id}"}
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


def test_talentverse_reports_requires_bearer_token(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get("/api/v1/talentverse/reports")

    assert response.status_code == 401


def test_talentverse_reports_returns_503_when_token_is_not_configured(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", None)
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 503


def test_talentverse_reports_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")

    response = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 403


def test_talentverse_reports_lists_only_published_reports(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)
    _add_report(db_session, slug="failed-report", version=7, status="failed")
    _add_report(db_session, slug="draft-report", version=8, status="draft")

    response = client.get(
        "/api/v1/talentverse/reports?region=global&status=published&limit=20",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["slug"] == "global-talentverse-report-2026-05-24-v6"
    assert payload["items"][0]["keySignals"][0]["signal"] == "全球招聘活动短期收缩"
    assert "article" not in payload["items"][0]
    assert payload["pageInfo"]["limit"] == 20


def test_talentverse_reports_rejects_invalid_cursor(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports?cursor=bad-cursor",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 422


def test_talentverse_reports_rejects_invalid_region(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")

    response = client.get(
        "/api/v1/talentverse/reports?region=unknown",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 422


def test_talentverse_reports_rate_limits_by_client_host(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    monkeypatch.setattr("app.api.talentverse_auth.RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr("app.api.talentverse_auth._REQUEST_LOG", {})

    first = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )
    second = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_talentverse_reports_supports_updated_after_filter(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    old_time = datetime(2026, 5, 20, 10, 0, 0)
    new_time = old_time + timedelta(days=4)
    _add_report(db_session, slug="old-report", version=1, updated_at=old_time)
    _add_report(db_session, slug="new-report", version=2, updated_at=new_time)

    response = client.get(
        "/api/v1/talentverse/reports?updatedAfter=2026-05-21T00:00:00",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["new-report"]


def test_talentverse_report_detail_returns_full_payload(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports/global-talentverse-report-2026-05-24-v6",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "global-talentverse-report-2026-05-24-v6"
    assert "marketStructure" in payload
    assert "faq" in payload
    assert payload["article"]["sections"][0]["heading"] == "市场发生了什么"
    assert payload["status"] == "published"


def test_talentverse_report_detail_hides_failed_report(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="failed-report", version=7, status="failed")

    response = client.get(
        "/api/v1/talentverse/reports/failed-report",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 404


def test_talentverse_report_detail_hides_draft_report(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="draft-report", version=8, status="draft")

    response = client.get(
        "/api/v1/talentverse/reports/draft-report",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 404
