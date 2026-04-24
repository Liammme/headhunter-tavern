from datetime import datetime, timedelta

from app.models import Job
from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue


def build_job(
    *,
    company: str,
    title: str,
    days_ago: int,
    description: str,
    signal_tags: dict | None = None,
) -> Job:
    current = datetime(2026, 4, 23, 12, 0, 0) - timedelta(days=days_ago)
    return Job(
        canonical_url=f"https://jobs.example.com/{company.lower()}/{title.lower().replace(' ', '-')}",
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=current,
        collected_at=current,
        bounty_grade="high",
        signal_tags=signal_tags
        or {
            "display_tags": ["AI"],
            "company_url": f"https://{company.lower()}.example.com",
        },
    )


def test_load_company_jobs_for_clue_uses_same_14_day_window_as_home_feed(db_session):
    db_session.add(
        build_job(
            company="OpenGradient",
            title="Recent Role",
            days_ago=2,
            description="urgent ai platform hiring now",
        )
    )
    db_session.add(
        build_job(
            company="OpenGradient",
            title="Old Role",
            days_ago=20,
            description="old archived role",
        )
    )
    db_session.commit()

    jobs = load_company_jobs_for_clue(
        db_session,
        company="OpenGradient",
        today=datetime(2026, 4, 23, 12, 0, 0).date(),
    )

    assert [job.title for job in jobs] == ["Recent Role"]


def test_build_company_clue_context_exposes_grounded_evidence_cards():
    jobs = [
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            days_ago=1,
            description=(
                "Urgent AI platform hiring. Build model infra for customer delivery. "
                "careers@opengradient.ai"
            ),
            signal_tags={
                "display_tags": ["AI", "Senior", "核心岗位"],
                "company_url": "https://opengradient.ai",
                "apply_url": "https://opengradient.ai/careers",
                "estimated_bounty_amount": 150000,
                "estimated_bounty_label": "¥120,000-¥180,000",
                "estimated_bounty_min": 120000,
                "estimated_bounty_max": 180000,
                "estimated_bounty_rate_pct": 20,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        )
    ]

    context = build_company_clue_context(
        company="OpenGradient",
        jobs=jobs,
        today=datetime(2026, 4, 23, 12, 0, 0).date(),
    )

    assert context["window"]["window_days"] == 14
    assert context["summary"]["total_jobs"] == 1
    assert context["summary"]["estimated_bounty"]["amount"] == 150000
    assert context["evidence_cards"][0]["title"] == "Principal AI Engineer"
    assert context["evidence_cards"][0]["entry_points"]["hiring_page"] == "https://opengradient.ai/careers"
    assert context["evidence_cards"][0]["evidence_snippets"]
    assert context["entry_points"]["job_posts"] == [jobs[0].canonical_url]
