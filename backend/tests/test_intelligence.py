from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, FeedMetadata, JobFeedSnapshot
from app.services.intelligence import build_intelligence_snapshot


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
