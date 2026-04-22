from datetime import datetime

from app.models import Job
from app.core.config import settings
from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, FeedMetadata, JobFeedSnapshot
from app.services.intelligence import (
    build_intelligence_snapshot,
    build_intelligence_system_prompt,
    build_intelligence_user_prompt,
    build_llm_intelligence_input,
    parse_llm_intelligence_fields,
    validate_llm_intelligence_fields,
)


def test_build_intelligence_snapshot_uses_day_payloads_as_shared_baseline():
    day_payloads = [
        DayBucketSnapshot(
            bucket="today",
            companies=[
                CompanyFeedSnapshot(
                    company="OpenGradient",
                    company_grade="focus",
                    total_jobs=2,
                    claimed_names=["Liam"],
                    jobs=[
                        JobFeedSnapshot(
                            id=1,
                            title="Principal AI Engineer",
                            canonical_url="https://example.com/1",
                            bounty_grade="high",
                            tags=["AI", "Senior", "核心岗位"],
                            claimed_names=["Liam"],
                        ),
                        JobFeedSnapshot(
                            id=2,
                            title="Senior Applied Scientist",
                            canonical_url="https://example.com/2",
                            bounty_grade="medium",
                            tags=["AI", "Senior", "关键扩张"],
                            claimed_names=[],
                        ),
                    ],
                ),
                CompanyFeedSnapshot(
                    company="Beta Labs",
                    company_grade="watch",
                    total_jobs=1,
                    claimed_names=[],
                    jobs=[
                        JobFeedSnapshot(
                            id=3,
                            title="Growth Manager",
                            canonical_url="https://example.com/3",
                            bounty_grade="medium",
                            tags=["增长", "高 BD 切入口"],
                            claimed_names=[],
                        )
                    ],
                ),
            ],
        )
    ]

    snapshot = build_intelligence_snapshot(
        day_payloads,
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert snapshot["headline"] == "近 14 天 AI 岗位活跃，建议优先跟进高赏金与重点公司。"
    assert snapshot["summary"] == "基于近 14 天统一聚合结果生成：2 家公司，3 个岗位，1 个高赏金岗位。"
    assert snapshot["analysis_version"] == "feed-v1"
    assert snapshot["rule_version"] == "score-v2"
    assert "重点公司 1 家，优先顺着公司卡往下打。" in snapshot["findings"]
    assert "已认领 1 个岗位，继续优先补齐未认领高赏金岗位。" in snapshot["findings"]
    assert snapshot["actions"][0] == "先看重点公司，再优先认领其中的高赏金岗位。"


def test_build_intelligence_snapshot_handles_empty_day_payloads():
    snapshot = build_intelligence_snapshot(
        [],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert snapshot == {
        "headline": "近 14 天岗位池暂无新增信号，建议先触发抓取更新。",
        "summary": "当前情报基于统一聚合结果生成，但窗口内还没有可展示的公司与岗位。",
        "analysis_version": "feed-v1",
        "rule_version": "score-v2",
        "window_start": "2026-04-05",
        "window_end": "2026-04-18",
        "generated_at": "2026-04-18T09:00:00",
        "findings": [
            "首页和情报当前共享同一聚合基线，因此这里为空时首页列表也应为空。",
        ],
        "actions": [
            "先触发抓取，等统一聚合结果生成后再判断主线方向。",
        ],
    }


def test_build_intelligence_snapshot_prefers_llm_when_project_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", "project-only-key")

    captured = {}

    def fake_generate(day_payloads, meta, jobs):
        captured["day_payloads"] = day_payloads
        captured["meta"] = meta
        captured["jobs"] = jobs
        return {
            "headline": "LLM 判断今天先打 AI 核心产研。",
            "summary": "真实模型基于统一聚合结果判断，建议先打重点公司与高赏金岗位。",
            "findings": ["AI 主线继续增强。"],
            "actions": ["优先认领未认领高赏金岗位。"],
        }

    monkeypatch.setattr("app.services.intelligence.generate_llm_intelligence_fields", fake_generate)

    day_payloads = [
        DayBucketSnapshot(
            bucket="today",
            companies=[
                CompanyFeedSnapshot(
                    company="OpenGradient",
                    company_grade="focus",
                    total_jobs=1,
                    claimed_names=[],
                    jobs=[
                        JobFeedSnapshot(
                            id=1,
                            title="Principal AI Engineer",
                            canonical_url="https://example.com/1",
                            bounty_grade="high",
                            tags=["AI", "核心岗位"],
                            claimed_names=[],
                        )
                    ],
                )
            ],
        )
    ]
    meta = FeedMetadata(
        analysis_version="feed-v1",
        rule_version="score-v2",
        window_start="2026-04-05",
        window_end="2026-04-18",
        generated_at="2026-04-18T09:00:00",
    )

    snapshot = build_intelligence_snapshot(day_payloads, meta)

    assert captured["day_payloads"] == day_payloads
    assert captured["meta"] == meta
    assert captured["jobs"] == []
    assert snapshot["headline"] == "LLM 判断今天先打 AI 核心产研。"
    assert snapshot["summary"] == "真实模型基于统一聚合结果判断，建议先打重点公司与高赏金岗位。"
    assert snapshot["findings"] == ["AI 主线继续增强。"]
    assert snapshot["actions"] == ["优先认领未认领高赏金岗位。"]
    assert snapshot["analysis_version"] == "feed-v1"
    assert snapshot["rule_version"] == "score-v2"


def test_build_intelligence_snapshot_falls_back_when_llm_fails(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", "project-only-key")

    def fake_generate(*_args, **_kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr("app.services.intelligence.generate_llm_intelligence_fields", fake_generate)

    snapshot = build_intelligence_snapshot(
        [
            DayBucketSnapshot(
                bucket="today",
                companies=[
                    CompanyFeedSnapshot(
                        company="OpenGradient",
                        company_grade="focus",
                        total_jobs=1,
                        claimed_names=[],
                        jobs=[
                            JobFeedSnapshot(
                                id=1,
                                title="Principal AI Engineer",
                                canonical_url="https://example.com/1",
                                bounty_grade="high",
                                tags=["AI", "Senior", "核心岗位"],
                                claimed_names=[],
                            )
                        ],
                    )
                ],
            )
        ],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert snapshot["headline"] == "近 14 天 AI 岗位活跃，建议优先跟进高赏金与重点公司。"
    assert snapshot["summary"] == "基于近 14 天统一聚合结果生成：1 家公司，1 个岗位，1 个高赏金岗位。"


def test_parse_llm_intelligence_fields_accepts_json_code_fence():
    payload = parse_llm_intelligence_fields(
        """```json
{"headline":"今天先盯 AI 核心岗","summary":"重点公司和高赏金岗位继续走强。","findings":["AI 产研是主线","重点公司集中出现","未认领高赏金仍有空间"],"actions":["先扫重点公司","优先认领高赏金","补公司判断"]}
```"""
    )

    assert payload == {
        "headline": "今天先盯 AI 核心岗",
        "summary": "重点公司和高赏金岗位继续走强。",
        "findings": ["AI 产研是主线", "重点公司集中出现", "未认领高赏金仍有空间"],
        "actions": ["先扫重点公司", "优先认领高赏金", "补公司判断"],
    }


def test_build_intelligence_snapshot_retries_with_fallback_models(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", "project-only-key")
    monkeypatch.setattr(settings, "bounty_pool_zhipu_model", "broken-model")
    monkeypatch.setattr(settings, "bounty_pool_zhipu_fallback_models", "glm-4-flash-250414,glm-4.7-flash")

    called_models = []

    def fake_request(_payload, model_name):
        called_models.append(model_name)
        if model_name == "broken-model":
            raise RuntimeError("bad request")
        return (
            '{"headline":"James侦探把杯子往吧台边一推：今天先盯高赏金产研岗。",'
            '"summary":"他说今天冒头的不是散岗，而是往重点公司收拢的核心岗位。",'
            '"findings":["你示意他继续，他低声补了一句：这波变化说明近14天里真正升温的是卡业务的产研岗，不是热闹标签。"],'
            '"actions":["他临走前只留一句：今天先盯重点公司里的高赏金技术、AI和产品岗。"]}'
        )

    monkeypatch.setattr(
        "app.services.intelligence._request_zhipu_chat_completion_with_model",
        fake_request,
    )

    snapshot = build_intelligence_snapshot(
        [
            DayBucketSnapshot(
                bucket="today",
                companies=[
                    CompanyFeedSnapshot(
                        company="OpenGradient",
                        company_grade="focus",
                        total_jobs=1,
                        claimed_names=[],
                        jobs=[
                            JobFeedSnapshot(
                                id=1,
                                title="Principal AI Engineer",
                                canonical_url="https://example.com/1",
                                bounty_grade="high",
                                tags=["AI", "Senior", "核心岗位"],
                                claimed_names=[],
                            )
                        ],
                    )
                ],
            )
        ],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert called_models == ["broken-model", "glm-4-flash-250414"]
    assert snapshot["headline"] == "James侦探把杯子往吧台边一推：今天先盯高赏金产研岗。"


def test_build_llm_intelligence_input_uses_fact_briefs_instead_of_raw_description():
    llm_input = build_llm_intelligence_input(
        [
            DayBucketSnapshot(
                bucket="today",
                companies=[
                    CompanyFeedSnapshot(
                        company="OpenGradient",
                        company_grade="focus",
                        total_jobs=1,
                        claimed_names=["Liam"],
                        jobs=[
                            JobFeedSnapshot(
                                id=1,
                                title="Staff AI Engineer",
                                canonical_url="https://example.com/1",
                                bounty_grade="high",
                                tags=["AI", "Senior", "核心岗位"],
                                claimed_names=["Liam"],
                            )
                        ],
                    )
                ],
            )
        ],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
        jobs=[
            Job(
                id=1,
                canonical_url="https://example.com/1",
                source_name="test",
                title="Staff AI Engineer",
                company="OpenGradient",
                company_normalized="opengradient",
                description="Urgent hire for a founding AI platform lead. Own LLM roadmap and infra delivery.",
                posted_at=datetime(2026, 4, 18, 9, 0, 0),
                collected_at=datetime(2026, 4, 18, 9, 0, 0),
                job_category="AI/算法",
                domain_tag="AI",
                bounty_grade="high",
                signal_tags={"display_tags": ["AI", "Senior", "核心岗位"]},
            )
        ],
    )

    assert "job_fact_briefs" in llm_input
    assert llm_input["job_fact_briefs"][0]["company"] == "OpenGradient"
    assert llm_input["job_fact_briefs"][0]["category"] == "AI/算法"
    assert llm_input["job_fact_briefs"][0]["domain_tag"] == "AI"
    assert llm_input["job_fact_briefs"][0]["seniority"] == "staff"
    assert llm_input["job_fact_briefs"][0]["urgent"] is True
    assert "urgent" in llm_input["job_fact_briefs"][0]["time_pressure_signals"]
    assert "claimed_names" not in llm_input["focus_companies"][0]
    assert "claimed_names" not in llm_input["representative_jobs"][0]
    assert "claimed_names" not in llm_input["job_fact_briefs"][0]
    assert "description" not in llm_input["job_fact_briefs"][0]


def test_intelligence_prompts_include_james_style_and_banned_rules():
    system_prompt = build_intelligence_system_prompt()
    user_prompt = build_intelligence_user_prompt({"overview": {"job_count": 1}})

    assert "James侦探" in system_prompt
    assert "250 到 400 字" in system_prompt
    assert "认领人只表示内部占坑状态" in system_prompt
    assert "禁止纯统计播报" in system_prompt
    assert "禁止空泛建议" in system_prompt
    assert "不要做标签播报" in user_prompt


def test_validate_llm_intelligence_fields_rejects_claimed_names():
    payload = {
        "headline": "James侦探把杯子往吧台边一推：今天先盯高赏金产研岗。",
        "summary": "他说今天真正冒头的是高赏金核心岗。",
        "findings": ["你示意他继续，他低声补了一句：验收测试员已经认领了这条线。"],
        "actions": ["他最后只留一句：先盯重点公司。"],
    }

    try:
        validate_llm_intelligence_fields(payload, banned_names={"验收测试员"})
    except Exception as exc:
        assert "claimed_names" in str(exc)
    else:
        raise AssertionError("expected claimed_names validation failure")


def test_validate_llm_intelligence_fields_rejects_stat_broadcast():
    payload = {
        "headline": "James侦探把杯子往吧台边一推：今天先盯 AI 主线。",
        "summary": "他说今天变化不在噪音，在高赏金岗位开始往重点公司收拢。",
        "findings": ["你示意他继续，他只回了一句：AI标签出现很多次，Web3标签达25次。"],
        "actions": ["他最后只留一句：先盯重点公司里的高赏金产研岗。"],
    }

    try:
        validate_llm_intelligence_fields(payload, banned_names=set())
    except Exception as exc:
        assert "tag count broadcast" in str(exc)
    else:
        raise AssertionError("expected stat broadcast validation failure")


def test_build_intelligence_snapshot_falls_back_when_output_uses_claimed_name(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", "project-only-key")

    def fake_generate(*_args, **_kwargs):
        raise RuntimeError("LLM response leaked claimed_names")

    monkeypatch.setattr("app.services.intelligence.generate_llm_intelligence_fields", fake_generate)

    snapshot = build_intelligence_snapshot(
        [
            DayBucketSnapshot(
                bucket="today",
                companies=[
                    CompanyFeedSnapshot(
                        company="OpenGradient",
                        company_grade="focus",
                        total_jobs=1,
                        claimed_names=["Liam"],
                        jobs=[
                            JobFeedSnapshot(
                                id=1,
                                title="Principal AI Engineer",
                                canonical_url="https://example.com/1",
                                bounty_grade="high",
                                tags=["AI", "Senior", "核心岗位"],
                                claimed_names=["Liam"],
                            )
                        ],
                    )
                ],
            )
        ],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert snapshot["headline"] == "近 14 天 AI 岗位活跃，建议优先跟进高赏金与重点公司。"


def test_generate_llm_intelligence_fields_repairs_invalid_first_draft(monkeypatch):
    from app.services.intelligence import generate_llm_intelligence_fields

    first = '{"headline":"分析报告","summary":"本周市场动态显示 AI标签出现很多次。","findings":["AI标签很多。"],"actions":["制定专项方案。"]}'
    repaired = (
        '{"headline":"James侦探晃了晃杯底：今天先盯重点公司里重新抬头的高赏金产研岗。",'
        '"summary":"他说，和近14天摊开的盘子比，今天更明显的变化不是热闹标签，而是高赏金岗位重新往重点公司和卡业务节奏的团队收拢。",'
        '"findings":["你示意他继续，他把话说透：这说明企业现在更急着把真正会拖慢产品和交付节奏的技术、AI、产品岗位往外放，而不是单纯补普通编制。"],'
        '"actions":["他把杯子推回来，只留一句：今天先盯重点公司和持续招不动的团队，优先抢技术、AI、产品里的高赏金核心岗。"]}'
    )
    responses = [first, repaired]

    def fake_request(_messages):
        return responses.pop(0)

    monkeypatch.setattr("app.services.intelligence._request_zhipu_chat_completion_with_retry", fake_request)

    result = generate_llm_intelligence_fields(
        [
            DayBucketSnapshot(
                bucket="today",
                companies=[
                    CompanyFeedSnapshot(
                        company="OpenGradient",
                        company_grade="focus",
                        total_jobs=1,
                        claimed_names=["Liam"],
                        jobs=[
                            JobFeedSnapshot(
                                id=1,
                                title="Principal AI Engineer",
                                canonical_url="https://example.com/1",
                                bounty_grade="high",
                                tags=["AI", "Senior", "核心岗位"],
                                claimed_names=["Liam"],
                            )
                        ],
                    )
                ],
            )
        ],
        FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v2",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
        jobs=[],
    )

    assert result["headline"].startswith("James侦探")
