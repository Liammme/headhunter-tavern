from datetime import date, datetime

from sqlalchemy import select

from app.models import MarketIntelligenceSnapshot, TalentverseReport
from app.services import talentverse_report_generation as service


def _raw_snapshot(*, region: str = "global", version: int = 6) -> MarketIntelligenceSnapshot:
    generated_at = datetime(2026, 5, 24, 15, 30, 4)
    return MarketIntelligenceSnapshot(
        id=23,
        region=region,
        snapshot_date=date(2026, 5, 24),
        generated_at=generated_at,
        window_days=180,
        status="success",
        market_signal_payload={
            "data_quality": {"sample_count": 1189},
            "market_windows": {"window_days": 180},
        },
        report_payload={
            "living_report": {
                "kind": "living_market_report",
                "schema_version": "living-market-report-v1",
                "headline": "全球招聘市场短期显收缩，AI与数据核心岗位韧性依旧",
                "version": version,
                "mode": "incremental_update",
                "previous_snapshot_id": 20,
                "seed_window_days": 180,
                "generated_at": generated_at.isoformat(),
                "executive_summary": "近7天岗位数较30天下降67.1%，但AI、数据和资深技术岗位仍保持韧性。",
                "sections": [
                    {
                        "section_id": "market_structure",
                        "title": "市场结构",
                        "body": "AI/算法与数据岗位合计占比68.5%，数据岗位占比上升。",
                        "claim_ids": ["c1"],
                    }
                ],
                "claims": [
                    {
                        "claim_id": "c1",
                        "previous_claim_id": None,
                        "status": "new",
                        "claim": "近7天岗位数较30天下降67.1%。",
                        "confidence": "high",
                        "evidence_ids": ["fact-1561", "fact-1560"],
                        "evidence_notes": [
                            "fact-1561: Technical Program Manager III, ML Infrastructure Resource Management, Google Cloud",
                            "fact-1560: Software Engineer III, AI/ML, Google Workspace",
                        ],
                        "change_reason": "7d_vs_30d ratio=0.3287。",
                    }
                ],
                "watchlist": [
                    {
                        "topic": "数据工程和数据基础设施岗位是否继续扩张",
                        "why_watch": "如果数据岗位继续超过 AI/算法岗位，说明投入重心可能转向数据资产。",
                        "evidence_ids": ["fact-1561"],
                    }
                ],
                "data_quality": {
                    "sample_count": 1189,
                    "baseline_note": "当前可见岗位的历史基线，不代表完整真实半年历史。",
                },
            }
        },
    )


def _valid_talentverse_payload() -> dict:
    return {
        "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        "subtitle": "基于 Talent Signal 公开招聘信号样本生成的 Talentverse 前沿科技招聘市场观察",
        "executiveSummary": "过去 180 天的公开招聘信号显示，全球招聘活动出现短期收缩，但 AI、数据和资深技术岗位仍保持结构性需求。Talentverse 将这一变化理解为企业从广泛扩张转向更谨慎的关键岗位筛选。",
        "keySignals": [
            {
                "signal": "全球招聘活动短期收缩",
                "data": "近 7 天岗位数较 30 天下降 67.1%。",
                "interpretation": "Talentverse 将这理解为从广泛扩张招聘转向更谨慎的关键岗位筛选。",
                "hiringImplication": "企业仍在招聘，但更倾向于投入能直接影响基础设施、数据资产和 AI 应用落地的岗位。",
                "confidence": "high",
                "evidenceRefs": ["fact-1561", "fact-1560"],
            }
        ],
        "marketStructure": {
            "body": "市场结构显示，AI / 算法与数据岗位仍是前沿科技招聘中的核心需求。",
            "metrics": [
                {
                    "label": "AI / 算法 + 数据岗位占比",
                    "value": "68.5%",
                    "description": "招聘需求仍集中在技术和数据能力上。",
                }
            ],
        },
        "demandShift": {
            "body": "短期窗口显示岗位数量下降，但长期窗口仍能看到 AI、数据和资深技术岗位的稳定存在。",
            "metrics": [
                {
                    "label": "7 天岗位数变化",
                    "value": "-67.1%",
                    "description": "相对 30 天窗口出现明显短期收缩。",
                }
            ],
        },
        "talentStrategyImplications": [
            {
                "title": "关键岗位优先级应高于岗位数量扩张",
                "body": "企业应优先确认哪些岗位真正影响产品、数据基础设施、AI 应用落地和组织执行。",
            }
        ],
        "risksAndWatchlist": [
            {
                "topic": "数据工程和数据基础设施岗位是否继续扩张",
                "reason": "如果数据岗位继续超过 AI / 算法岗位，说明企业的人才投入重心可能从模型能力转向数据资产和工程化能力。",
                "evidenceRefs": ["fact-1561"],
            }
        ],
        "talentverseView": "Talentverse 认为，这轮变化说明前沿科技招聘市场正在从数量扩张转向高确定性招聘。",
        "methodologyNote": {
            "sampleCount": 1189,
            "windowDays": 180,
            "body": "数据来源为 Talent Signal，基于公开招聘信号和结构化样本，不代表完整市场全量。",
        },
        "faq": [
            {
                "question": "这篇报告对 AI 团队招聘意味着什么？",
                "answer": "AI 团队应关注数据基础设施、AI 应用落地和资深技术岗位，而不是只看岗位数量。",
            }
        ],
        "glossaryTerms": [
            {
                "term": "高确定性招聘",
                "definition": "一种优先关注证据质量、岗位影响和长期匹配度的关键人才招聘方式。",
            }
        ],
        "evidenceRefs": [
            {
                "id": "fact-1561",
                "note": "Technical Program Manager III, ML Infrastructure Resource Management, Google Cloud",
                "confidence": "high",
            }
        ],
        "seo": {
            "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
            "description": "Talentverse 前沿科技招聘报告：全球招聘活动短期收缩，但 AI、数据与资深技术岗位需求保持韧性。",
            "keywords": ["frontier tech hiring", "AI-native talent intelligence", "高确定性招聘"],
        },
    }


def test_build_slug_uses_region_date_and_version():
    snapshot = _raw_snapshot()

    assert service.build_talentverse_slug(snapshot) == "global-talentverse-report-2026-05-24-v6"


def test_validate_talentverse_payload_rejects_forbidden_raw_fields():
    payload = _valid_talentverse_payload()
    payload["canonical_url"] = "https://example.com/raw-job"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "forbidden field" in str(exc)
    else:
        raise AssertionError("expected forbidden field validation failure")


def test_validate_talentverse_payload_rejects_forbidden_raw_text():
    payload = _valid_talentverse_payload()
    payload["talentverseView"] = "不要暴露 canonical_url 或 full_description。"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "forbidden text" in str(exc)
    else:
        raise AssertionError("expected forbidden text validation failure")


def test_validate_talentverse_payload_rejects_invalid_nested_key_signal():
    payload = _valid_talentverse_payload()
    del payload["keySignals"][0]["hiringImplication"]

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "hiringImplication" in str(exc)
    else:
        raise AssertionError("expected nested schema validation failure")


def test_validate_talentverse_payload_rejects_extra_top_level_field():
    payload = _valid_talentverse_payload()
    payload["unexpected"] = "not allowed"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "unexpected fields" in str(exc)
    else:
        raise AssertionError("expected strict schema validation failure")


def test_validate_talentverse_payload_requires_watchlist_evidence_refs():
    payload = _valid_talentverse_payload()
    del payload["risksAndWatchlist"][0]["evidenceRefs"]

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "evidenceRefs" in str(exc)
    else:
        raise AssertionError("expected watchlist evidenceRefs validation failure")


def test_generate_talentverse_report_publishes_valid_payload(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    payload = _valid_talentverse_payload()

    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: service.json.dumps(payload))

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "published"
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert report.raw_report_id == snapshot.id
    assert report.slug == "global-talentverse-report-2026-05-24-v6"
    assert report.status == "published"
    assert report.payload["source"]["name"] == "Talent Signal"
    assert report.payload["status"] == "published"


def test_generate_talentverse_report_records_failed_without_raising(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()

    def fail_request(messages, timeout_seconds=None):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(service, "request_structured_json", fail_request)

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "failed"
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert report.status == "failed"
    assert "provider unavailable" in report.error_message


def test_generate_talentverse_report_skips_japan_in_first_version(db_session, monkeypatch):
    snapshot = _raw_snapshot(region="japan")
    db_session.add(snapshot)
    db_session.commit()

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "skipped"
    assert db_session.execute(select(TalentverseReport)).scalars().all() == []


def test_generate_talentverse_report_is_idempotent_for_published_raw_report(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    payload = _valid_talentverse_payload()
    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: service.json.dumps(payload))

    first = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)
    second = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    reports = db_session.execute(select(TalentverseReport)).scalars().all()
    assert first["status"] == "published"
    assert second["status"] == "published"
    assert len(reports) == 1
