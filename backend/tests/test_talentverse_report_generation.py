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
    article_body = (
        "## 招聘活动收缩，但不是关键岗位需求消失\n\n"
        "过去 180 天的公开招聘信号显示，全球招聘活动正在从广泛扩张转向更谨慎的关键岗位筛选。近 7 天岗位数较 30 天下降 67.1%，这个变化说明企业正在重新评估招聘节奏和岗位优先级。\n\n"
        "这种收缩并不等于关键岗位需求消失。AI、数据和资深技术岗位仍然保持结构性需求，说明前沿科技公司正在把有限招聘资源集中到更能影响产品交付、数据资产和 AI 应用落地的位置。\n\n"
        "## AI 与数据岗位为什么仍然保持韧性\n\n"
        "AI / 算法与数据岗位合计占比达到 68.5%，它们仍然构成前沿科技招聘的主要需求。这个比例意味着企业没有放弃技术投入，而是在收缩周期里优先保留与模型应用、数据工程和基础设施能力直接相关的岗位。\n\n"
        "数据岗位的变化尤其值得关注。数据岗位占比上升，说明企业对数据治理、数据平台和分析能力的依赖正在加深，招聘判断不能只看模型能力，也要看候选人能否把数据资产转化为可执行的产品和业务结果。\n\n"
        "## 关键人才招聘正在从数量转向判断质量\n\n"
        "Agent/RAG 相关岗位的变化显示，企业仍在寻找能推动 AI 应用进入真实业务流程的人才。相比泛泛扩张团队，这类岗位更强调工程落地、产品理解和跨职能协作。\n\n"
        "Senior 及以上岗位占比提升，也说明企业在不确定周期中更愿意投入能独立承担复杂任务的人。对新经济团队来说，关键不只是招更多人，而是判断哪些任务关键型人才能直接改变交付质量和组织速度。\n\n"
        "## 企业应该如何重新排序招聘优先级\n\n"
        "企业需要先确认哪些岗位真正影响业务结果，再决定是否进入招聘流程。数据基础设施、AI 应用落地、Agent/RAG、资深技术负责人和跨产品工程边界的人才，应该优先进入人才研究和候选人证据链判断。\n\n"
        "在这样的市场里，等待岗位数量恢复不是最好的策略。更稳妥的做法是缩小岗位范围，提高判断密度，把招聘资源投向具备明确业务影响和高证据质量的候选人。\n\n"
        "## Talentverse 判断\n\n"
        "Talentverse 判断，这轮变化说明前沿科技招聘市场正在从数量扩张进入高确定性招聘阶段。仍然值得优先投入的是 AI、数据、Agent/RAG、资深技术与产品人才，以及能够承担任务关键型工作的复合型候选人。\n\n"
        "企业最容易误判的是把招聘活动收缩理解为人才需求消失。真正发生的变化是判断标准变高，岗位优先级更集中，高确定性招聘因此会变得更重要。"
    )
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
        "article": {"format": "markdown", "body": article_body},
    }


def _valid_talentverse_payloads() -> list[dict]:
    payloads = []
    for locale in service.TALENTVERSE_LOCALES:
        payload = _valid_talentverse_payload()
        payload["title"] = f"{locale} Talentverse Report"
        payload["subtitle"] = f"{locale} Talentverse Research Insight"
        payload["seo"] = {
            **payload["seo"],
            "title": f"{locale} SEO title",
            "description": f"{locale} SEO description",
        }
        payloads.append(payload)
    return payloads


def _mock_llm_payloads(monkeypatch, payloads: list[dict]) -> None:
    responses = iter([service.json.dumps(payload) for payload in payloads])
    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: next(responses))


def test_build_slug_uses_region_date_and_version():
    snapshot = _raw_snapshot()

    assert service.build_talentverse_slug(snapshot) == "global-talentverse-report-2026-05-24-v6"
    assert service.build_talentverse_slug(snapshot, locale="en") == "global-talentverse-report-2026-05-24-v6-en"
    assert service.build_talentverse_slug(snapshot, locale="zh-TW") == "global-talentverse-report-2026-05-24-v6-zh-tw"
    assert service.build_talentverse_slug(snapshot, locale="ja-JP") == "global-talentverse-report-2026-05-24-v6-ja"


def test_build_talentverse_system_prompt_specifies_metric_item_schema():
    prompt = service.build_talentverse_system_prompt()

    assert "Every metrics item must be an object" in prompt
    assert "label, value, description" in prompt
    assert "Do not use metric, name, count, number" in prompt


def test_build_talentverse_system_prompt_specifies_seo_keywords_schema():
    prompt = service.build_talentverse_system_prompt()

    assert "seo.keywords must be a non-empty JSON array of strings" in prompt
    assert '"keywords":["frontier tech hiring"' in prompt
    assert "Return exactly this JSON shape" in prompt


def test_build_talentverse_system_prompt_specifies_article_schema():
    prompt = service.build_talentverse_system_prompt()
    en_prompt = service.build_talentverse_system_prompt(locale="en")

    assert "article.format must be exactly" in prompt
    assert "one complete Talentverse Research Insight in Markdown" in prompt
    assert "1200-1800 Chinese characters" in prompt
    assert "Talentverse 判断" in prompt
    assert "Target locale: en" in en_prompt
    assert "Do not simply translate another language version" in en_prompt


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


def test_validate_talentverse_payload_rejects_empty_seo_keywords():
    payload = _valid_talentverse_payload()
    payload["seo"]["keywords"] = []

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "seo.keywords" in str(exc)
    else:
        raise AssertionError("expected seo keywords validation failure")


def test_validate_talentverse_payload_rejects_blank_seo_keyword_item():
    payload = _valid_talentverse_payload()
    payload["seo"]["keywords"] = ["frontier tech hiring", ""]

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "non-empty strings" in str(exc)
    else:
        raise AssertionError("expected seo keyword item validation failure")


def test_validate_talentverse_payload_requires_markdown_article_format():
    payload = _valid_talentverse_payload()
    payload["article"]["format"] = "html"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "article.format" in str(exc)
    else:
        raise AssertionError("expected article format validation failure")


def test_validate_talentverse_payload_rejects_article_bullet_body():
    payload = _valid_talentverse_payload()
    payload["article"]["body"] = payload["article"]["body"] + "\n\n- 近 7 天岗位数较 30 天下降 67.1%。"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "continuous prose" in str(exc)
    else:
        raise AssertionError("expected article prose validation failure")


def test_validate_talentverse_payload_rejects_article_forbidden_modules():
    payload = _valid_talentverse_payload()
    payload["article"]["body"] = payload["article"]["body"].replace("## Talentverse 判断", "## FAQ")

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "article.body must not contain module" in str(exc)
    else:
        raise AssertionError("expected article module validation failure")


def test_generate_talentverse_report_publishes_valid_payload(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    _mock_llm_payloads(monkeypatch, _valid_talentverse_payloads())

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "published"
    assert result["locales"] == {
        "zh-CN": "global-talentverse-report-2026-05-24-v6",
        "en": "global-talentverse-report-2026-05-24-v6-en",
        "zh-TW": "global-talentverse-report-2026-05-24-v6-zh-tw",
        "ja-JP": "global-talentverse-report-2026-05-24-v6-ja",
    }
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert report.raw_report_id == snapshot.id
    assert report.slug == "global-talentverse-report-2026-05-24-v6"
    assert report.locale == "zh-CN"
    assert report.status == "published"
    assert report.payload["source"]["name"] == "Talent Signal"
    assert report.payload["article"]["format"] == "markdown"
    assert "## Talentverse 判断" in report.payload["article"]["body"]
    assert set(report.payload["translations"]) == {"zh-CN", "en", "zh-TW", "ja-JP"}
    assert report.payload["translations"]["en"]["slug"] == "global-talentverse-report-2026-05-24-v6-en"
    assert report.payload["translations"]["en"]["locale"] == "en"
    assert report.payload["translationGroupId"] == "global-talentverse-report-2026-05-24-v6"
    assert report.payload["alternates"]["ja-JP"]["slug"] == "global-talentverse-report-2026-05-24-v6-ja"
    assert report.payload["status"] == "published"


def test_generate_talentverse_report_publishes_available_locales_when_one_locale_fails(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    responses = iter(
        [
            service.json.dumps(_valid_talentverse_payload()),
            RuntimeError("provider unavailable for en"),
            service.json.dumps(_valid_talentverse_payload()),
            service.json.dumps(_valid_talentverse_payload()),
        ]
    )

    def fake_request(messages, timeout_seconds=None):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(service, "request_structured_json", fake_request)

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "published"
    assert "en" in result["failed_locales"]
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert "en" not in report.payload["alternates"]
    assert "en" not in report.payload["translations"]
    assert report.payload["translationFailures"]["en"] == "provider unavailable for en"


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
    _mock_llm_payloads(monkeypatch, _valid_talentverse_payloads())

    first = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)
    second = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    reports = db_session.execute(select(TalentverseReport)).scalars().all()
    assert first["status"] == "published"
    assert second["status"] == "published"
    assert len(reports) == 1


def test_generate_talentverse_report_force_regenerates_published_raw_report(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    first_payloads = _valid_talentverse_payloads()
    second_payloads = _valid_talentverse_payloads()
    second_payloads[0]["title"] = "更新后的 Talentverse 官网报告"
    responses = iter([service.json.dumps(payload) for payload in first_payloads + second_payloads])
    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: next(responses))

    first = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)
    second = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id, force=True)

    reports = db_session.execute(select(TalentverseReport)).scalars().all()
    assert first["status"] == "published"
    assert second["status"] == "published"
    assert len(reports) == 1
    assert reports[0].payload["title"] == "更新后的 Talentverse 官网报告"
