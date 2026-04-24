from datetime import datetime, timedelta

from app.models import Job
from app.services.feed_snapshot import FeedMetadata
from app.services.intelligence_context import build_intelligence_change_context


def build_job(
    *,
    job_id: int,
    company: str,
    company_normalized: str,
    title: str,
    days_ago: int,
    category: str = "技术",
    domain: str = "AI",
    bounty_grade: str = "medium",
    tags: list[str] | None = None,
) -> Job:
    base_time = datetime(2026, 4, 18, 9, 0, 0)
    posted_at = base_time - timedelta(days=days_ago)
    return Job(
        id=job_id,
        canonical_url=f"https://jobs.example.com/{company_normalized}/{job_id}",
        source_name="test",
        title=title,
        company=company,
        company_normalized=company_normalized,
        description="test",
        posted_at=posted_at,
        collected_at=posted_at,
        job_category=category,
        domain_tag=domain,
        bounty_grade=bounty_grade,
        signal_tags={"display_tags": tags or [domain, category]},
    )


def build_meta() -> FeedMetadata:
    return FeedMetadata(
        analysis_version="feed-v1",
        rule_version="score-v2",
        window_start="2026-04-05",
        window_end="2026-04-18",
        generated_at="2026-04-18T09:00:00",
    )


def test_change_context_identifies_new_companies_today_with_evidence():
    context = build_intelligence_change_context(
        jobs=[
            build_job(
                job_id=1,
                company="Legacy Co",
                company_normalized="legacy-co",
                title="Backend Engineer",
                days_ago=2,
            ),
            build_job(
                job_id=2,
                company="OpenGradient",
                company_normalized="opengradient",
                title="Staff AI Engineer",
                days_ago=0,
                category="AI/算法",
                domain="AI",
                bounty_grade="high",
                tags=["AI", "Senior", "核心岗位"],
            ),
        ],
        meta=build_meta(),
    )

    assert context["today_counts"]["job_count"] == 1
    assert context["yesterday_counts"]["job_count"] == 0
    assert context["baseline_counts"]["job_count"] == 1
    assert context["deltas"]["today_vs_yesterday"]["job_count"] == 1
    assert context["new_companies_today"][0]["company"] == "OpenGradient"
    assert context["new_companies_today"][0]["evidence"][0] == {
        "company": "OpenGradient",
        "title": "Staff AI Engineer",
        "canonical_url": "https://jobs.example.com/opengradient/2",
        "bucket": "today",
        "bounty_grade": "high",
        "tags": ["AI", "Senior", "核心岗位"],
        "category": "AI/算法",
        "domain_tag": "AI",
    }


def test_change_context_identifies_rising_categories_and_domains():
    context = build_intelligence_change_context(
        jobs=[
            build_job(
                job_id=1,
                company="OpenGradient",
                company_normalized="opengradient",
                title="Staff AI Engineer",
                days_ago=0,
                category="AI/算法",
                domain="AI",
                bounty_grade="high",
            ),
            build_job(
                job_id=2,
                company="VectorWorks",
                company_normalized="vectorworks",
                title="Applied AI Engineer",
                days_ago=0,
                category="AI/算法",
                domain="AI",
                bounty_grade="medium",
            ),
            build_job(
                job_id=3,
                company="Legacy Co",
                company_normalized="legacy-co",
                title="Operations Manager",
                days_ago=1,
                category="运营",
                domain="企业服务",
                bounty_grade="low",
            ),
            build_job(
                job_id=4,
                company="Beta Labs",
                company_normalized="beta-labs",
                title="Backend Engineer",
                days_ago=5,
                category="技术",
                domain="SaaS",
                bounty_grade="medium",
            ),
        ],
        meta=build_meta(),
    )

    assert context["top_rising_categories"][0]["category"] == "AI/算法"
    assert context["top_rising_categories"][0]["today_count"] == 2
    assert context["top_rising_domains"][0]["domain_tag"] == "AI"
    assert context["top_rising_domains"][0]["today_count"] == 2
    assert context["representative_changes"][0]["change_type"] in {
        "new_company_today",
        "rising_category",
        "rising_domain",
    }


def test_change_context_returns_stable_fallback_when_today_has_no_changes():
    context = build_intelligence_change_context(
        jobs=[
            build_job(
                job_id=1,
                company="Legacy Co",
                company_normalized="legacy-co",
                title="Backend Engineer",
                days_ago=2,
            ),
        ],
        meta=build_meta(),
    )

    assert context["today_counts"]["job_count"] == 0
    assert context["new_companies_today"] == []
    assert context["rising_companies"] == []
    assert context["top_rising_categories"] == []
    assert context["top_rising_domains"] == []
    assert context["representative_changes"] == [
        {
            "change_type": "no_today_change",
            "summary": "今天暂无可验证的新变化，情报应降级为稳定提示。",
            "evidence": [],
        }
    ]


def test_change_context_uses_collected_at_when_posted_at_is_missing():
    job = build_job(
        job_id=1,
        company="OpenGradient",
        company_normalized="opengradient",
        title="Staff AI Engineer",
        days_ago=0,
    )
    job.posted_at = None

    context = build_intelligence_change_context(jobs=[job], meta=build_meta())

    assert context["today_counts"]["job_count"] == 1
    assert context["new_companies_today"][0]["company"] == "OpenGradient"


def test_change_context_dedupes_company_by_normalized_key():
    context = build_intelligence_change_context(
        jobs=[
            build_job(
                job_id=1,
                company="Open Gradient",
                company_normalized="opengradient",
                title="Staff AI Engineer",
                days_ago=0,
            ),
            build_job(
                job_id=2,
                company="OpenGradient",
                company_normalized="opengradient",
                title="Applied AI Engineer",
                days_ago=0,
            ),
        ],
        meta=build_meta(),
    )

    assert context["today_counts"]["company_count"] == 1
    assert len(context["new_companies_today"]) == 1
    assert context["new_companies_today"][0]["today_count"] == 2
