from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob
from app.models import Job, JobClaim
from app.services.job_enrichment import build_job_payload
from app.services.home_feed_aggregation import build_day_payloads


def enable_estimated_bounty_read(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.home_feed_aggregation._should_expose_estimated_bounty",
        lambda: True,
    )


def build_job(
    *,
    job_id: int,
    company: str,
    company_normalized: str,
    title: str,
    bounty_grade: str,
    days_ago: int,
    job_category: str = "技术",
    tags: list[str] | None = None,
    company_url: str | None = None,
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
        bounty_grade=bounty_grade,
        job_category=job_category,
        signal_tags={
            "display_tags": tags or [],
            **({"company_url": company_url} if company_url else {}),
        },
    )


def build_claim(*, claim_id: int, job_id: int, claimer_name: str) -> JobClaim:
    return JobClaim(
        id=claim_id,
        job_id=job_id,
        claimer_name=claimer_name,
        created_at=datetime(2026, 4, 18, 10, claim_id, 0),
    )


def test_build_day_payloads_sorts_companies_jobs_and_claims():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
            job_category="AI/算法",
            tags=["AI", "Senior"],
        ),
        build_job(
            job_id=2,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Product Manager",
            bounty_grade="medium",
            days_ago=0,
            job_category="产品",
            tags=["产品"],
        ),
        build_job(
            job_id=3,
            company="Beta Labs",
            company_normalized="beta-labs",
            title="Backend Engineer",
            bounty_grade="low",
            days_ago=0,
            job_category="技术",
            tags=["技术"],
        ),
    ]
    claims = [
        build_claim(claim_id=1, job_id=2, claimer_name="Mina"),
        build_claim(claim_id=2, job_id=1, claimer_name="Leo"),
        build_claim(claim_id=3, job_id=1, claimer_name="Mina"),
    ]

    payloads = build_day_payloads(jobs, claims, today=datetime(2026, 4, 18).date())

    assert [day.bucket for day in payloads] == ["within_3_days"]
    companies = payloads[0].companies
    assert [company.company for company in companies] == ["OpenGradient", "Beta Labs"]
    assert companies[0].company_grade == "watch"
    assert companies[0].company_url is None
    assert [job.id for job in companies[0].jobs] == [1, 2]
    assert [job.job_category for job in companies[0].jobs] == ["AI/算法", "产品"]
    assert companies[0].claimed_names == ["Leo", "Mina"]
    assert companies[0].claimed_by == "Leo"
    assert companies[0].claim_status == "claimed"
    assert [job.claimed_names for job in companies[0].jobs] == [[], []]


def test_build_day_payloads_filters_jobs_outside_window():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        ),
        build_job(
            job_id=2,
            company="Legacy Co",
            company_normalized="legacy-co",
            title="Old Role",
            bounty_grade="medium",
            days_ago=20,
        ),
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert len(payloads) == 1
    assert payloads[0].bucket == "within_3_days"
    assert [company.company for company in payloads[0].companies] == ["OpenGradient"]


def test_build_day_payloads_derives_category_from_legacy_display_tags():
    jobs = [
        build_job(
            job_id=1,
            company="Legacy Data Co",
            company_normalized="legacy-data-co",
            title="Data Engineer",
            bounty_grade="medium",
            days_ago=0,
            job_category="其他",
            tags=["AI", "数据", "关键扩张"],
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].jobs[0].job_category == "数据"


def test_build_day_payloads_normalizes_legacy_growth_category():
    jobs = [
        build_job(
            job_id=1,
            company="Legacy Growth Co",
            company_normalized="legacy-growth-co",
            title="Growth Manager",
            bounty_grade="medium",
            days_ago=0,
            job_category="增长",
            tags=["Web3", "增长"],
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].jobs[0].job_category == "市场"


def test_build_day_payloads_falls_back_to_title_classifier_for_legacy_jobs():
    jobs = [
        build_job(
            job_id=1,
            company="Legacy Design Co",
            company_normalized="legacy-design-co",
            title="Graphic Designer",
            bounty_grade="medium",
            days_ago=0,
            job_category="其他",
            tags=["Web3", "长期挂岗"],
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].jobs[0].job_category == "设计"


def test_build_day_payloads_uses_high_confidence_title_category_over_legacy_category():
    jobs = [
        build_job(
            job_id=1,
            company="Legacy Product Co",
            company_normalized="legacy-product-co",
            title="Product Designer",
            bounty_grade="medium",
            days_ago=0,
            job_category="产品",
            tags=["Web3", "产品", "长期挂岗"],
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].jobs[0].job_category == "设计"


def test_build_day_payloads_keeps_explicit_signal_category_before_title_classifier():
    jobs = [
        build_job(
            job_id=1,
            company="Signal Category Co",
            company_normalized="signal-category-co",
            title="Product Designer",
            bounty_grade="medium",
            days_ago=0,
            job_category="产品",
            tags=["Web3", "产品", "长期挂岗"],
        )
    ]
    jobs[0].signal_tags["job_category"] = "产品"

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].jobs[0].job_category == "产品"


def test_build_day_payloads_uses_non_overlapping_recent_buckets():
    jobs = [
        build_job(
            job_id=1,
            company="Recent Co",
            company_normalized="recent-co",
            title="Recent Role",
            bounty_grade="high",
            days_ago=2,
        ),
        build_job(
            job_id=2,
            company="Week Co",
            company_normalized="week-co",
            title="Week Role",
            bounty_grade="medium",
            days_ago=3,
        ),
        build_job(
            job_id=3,
            company="Earlier Co",
            company_normalized="earlier-co",
            title="Earlier Role",
            bounty_grade="low",
            days_ago=7,
        ),
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert [day.bucket for day in payloads] == ["within_3_days", "within_7_days", "earlier"]
    assert [day.companies[0].company for day in payloads] == ["Recent Co", "Week Co", "Earlier Co"]


def test_build_day_payloads_company_grade_follows_v2_backed_bounty_grades(monkeypatch):
    posted_at = datetime(2026, 4, 18, 9, 0, 0)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls):
            return posted_at

    monkeypatch.setattr("app.services.job_facts.datetime", FixedDatetime)
    normalized_jobs = [
        NormalizedJob(
            source_job_id="principal-1",
            canonical_url="https://jobs.example.com/opengradient/principal-ai-engineer-1",
            title="Principal AI Engineer",
            company="OpenGradient",
            location="Remote",
            remote_type="remote",
            employment_type="full-time",
            description="Build LLM platform and hiring roadmap.",
            posted_at=posted_at,
            raw_payload={"site": "test-board"},
        ),
        NormalizedJob(
            source_job_id="principal-2",
            canonical_url="https://jobs.example.com/opengradient/principal-ai-engineer-2",
            title="Principal AI Engineer",
            company="OpenGradient",
            location="Remote",
            remote_type="remote",
            employment_type="full-time",
            description="Build LLM platform and hiring roadmap.",
            posted_at=posted_at,
            raw_payload={"site": "test-board"},
        ),
        NormalizedJob(
            source_job_id="ops-1",
            canonical_url="https://jobs.example.com/opengradient/ops-role",
            title="Operations Coordinator",
            company="OpenGradient",
            location="Remote",
            remote_type="remote",
            employment_type="full-time",
            description="Support internal operations.",
            posted_at=posted_at,
            raw_payload={"site": "test-board"},
        ),
    ]

    jobs = []
    for idx, normalized_job in enumerate(normalized_jobs, start=1):
        payload = build_job_payload(normalized_job)
        jobs.append(Job(id=idx, **payload))

    payloads = build_day_payloads(jobs, [], today=posted_at.date())

    assert payloads[0].companies[0].company_grade == "watch"
    assert [job.bounty_grade for job in payloads[0].companies[0].jobs] == ["medium", "medium", "low"]


def test_build_day_payloads_preserves_company_url_for_company_card():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
            company_url="https://jobs.example.com/companies/opengradient",
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    assert payloads[0].companies[0].company_url == "https://jobs.example.com/companies/opengradient"


def test_build_day_payloads_emits_company_level_claim_subject():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        ),
        build_job(
            job_id=2,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Product Manager",
            bounty_grade="medium",
            days_ago=0,
        ),
    ]
    claims = [build_claim(claim_id=1, job_id=1, claimer_name="Mina")]

    payloads = build_day_payloads(jobs, claims, today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.claimed_names == ["Mina"]
    assert company.claimed_by == "Mina"
    assert company.claim_status == "claimed"
    assert [job.claimed_names for job in company.jobs] == [[], []]


def test_build_day_payloads_emits_company_level_estimated_bounty_when_present(monkeypatch):
    enable_estimated_bounty_read(monkeypatch)
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        )
    ]
    jobs[0].signal_tags.update(
        {
            "estimated_bounty_amount": 12600,
            "estimated_bounty_label": "¥7,200-¥18,000",
            "estimated_bounty_min": 7200,
            "estimated_bounty_max": 18000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        }
    )

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount == 12600
    assert company.estimated_bounty_label == "¥7,200-¥18,000"
    assert not hasattr(company.jobs[0], "estimated_bounty_amount")
    assert not hasattr(company.jobs[0], "estimated_bounty_label")


def test_build_day_payloads_keeps_persisted_estimated_bounty_values(monkeypatch):
    enable_estimated_bounty_read(monkeypatch)
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        )
    ]
    jobs[0].signal_tags.update(
        {
            "estimated_bounty_amount": 12600,
            "estimated_bounty_label": "¥7,200-¥18,000",
            "estimated_bounty_min": 7200,
            "estimated_bounty_max": 18000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        }
    )

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount == 12600
    assert company.estimated_bounty_label == "¥7,200-¥18,000"


def test_build_day_payloads_hides_estimated_bounty_when_rollout_flag_disabled(monkeypatch):
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        )
    ]
    jobs[0].signal_tags.update(
        {
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
            "estimated_bounty_min": 120000,
            "estimated_bounty_max": 180000,
            "estimated_bounty_rate_pct": 20,
            "estimated_bounty_rule_version": "bounty-rule-v1",
            "estimated_bounty_confidence": "medium",
        }
    )
    monkeypatch.setattr(
        "app.services.home_feed_aggregation._should_expose_estimated_bounty",
        lambda: False,
        raising=False,
    )

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount is None
    assert company.estimated_bounty_label == "待估算"


def test_build_day_payloads_uses_top_ranked_job_estimate_for_company_card(monkeypatch):
    enable_estimated_bounty_read(monkeypatch)
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Operations Coordinator",
            bounty_grade="low",
            days_ago=0,
        ),
        build_job(
            job_id=2,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Principal AI Engineer",
            bounty_grade="high",
            days_ago=0,
        ),
    ]
    jobs[0].signal_tags.update(
        {
            "estimated_bounty_amount": 6000,
            "estimated_bounty_label": "¥4,000-¥8,000",
            "estimated_bounty_min": 4000,
            "estimated_bounty_max": 8000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        }
    )
    jobs[1].signal_tags.update(
        {
            "estimated_bounty_amount": 12600,
            "estimated_bounty_label": "¥7,200-¥18,000",
            "estimated_bounty_min": 7200,
            "estimated_bounty_max": 18000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        }
    )

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert [job.id for job in company.jobs] == [2, 1]
    assert company.estimated_bounty_amount == 12600
    assert company.estimated_bounty_label == "¥7,200-¥18,000"


def test_build_day_payloads_falls_back_to_pending_estimate_when_missing():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        )
    ]

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount is None
    assert company.estimated_bounty_label == "待估算"
