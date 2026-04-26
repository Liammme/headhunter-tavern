from datetime import datetime

from app.models import Job
from app.services.bounty_backfill_service import backfill_estimated_bounties


def test_backfill_estimated_bounties_updates_jobs_missing_estimates(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/1",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Salary range: ¥30k-50k/month. Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={"display_tags": ["AI", "Senior", "核心岗位"]},
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 1, "skipped_jobs": 0}
    assert refreshed.signal_tags["estimated_bounty_amount"] == 12600
    assert refreshed.signal_tags["estimated_bounty_label"] == "¥7,200-¥18,000"
    assert refreshed.signal_tags["display_tags"] == ["AI", "Senior", "核心岗位"]


def test_backfill_estimated_bounties_skips_jobs_with_existing_estimates(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/2",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={
            "display_tags": ["AI", "Senior", "核心岗位"],
            "estimated_bounty_amount": 12600,
            "estimated_bounty_label": "¥7,200-¥18,000",
            "estimated_bounty_min": 7200,
            "estimated_bounty_max": 18000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        },
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 0, "skipped_jobs": 1}
    assert refreshed.signal_tags["estimated_bounty_amount"] == 12600
    assert refreshed.signal_tags["estimated_bounty_label"] == "¥7,200-¥18,000"


def test_backfill_estimated_bounties_clears_partial_estimate_snapshots_without_salary(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/3",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={
            "display_tags": ["AI", "Senior", "核心岗位"],
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
        },
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 1, "skipped_jobs": 0}
    assert "estimated_bounty_amount" not in refreshed.signal_tags
    assert "estimated_bounty_label" not in refreshed.signal_tags
    assert refreshed.signal_tags["display_tags"] == ["AI", "Senior", "核心岗位"]


def test_backfill_estimated_bounties_skips_missing_estimates_without_salary(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/5",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={"display_tags": ["AI", "Senior", "核心岗位"]},
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 0, "skipped_jobs": 1}
    assert refreshed.signal_tags == {"display_tags": ["AI", "Senior", "核心岗位"]}


def test_backfill_estimated_bounties_clears_invalid_estimate_snapshots_without_salary(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/4",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={
            "display_tags": ["AI", "Senior", "核心岗位"],
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
            "estimated_bounty_min": 160000,
            "estimated_bounty_max": 180000,
            "estimated_bounty_rate_pct": 25,
            "estimated_bounty_rule_version": "bounty-rule-v1",
            "estimated_bounty_confidence": "medium",
        },
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 1, "skipped_jobs": 0}
    assert "estimated_bounty_amount" not in refreshed.signal_tags
    assert "estimated_bounty_label" not in refreshed.signal_tags
    assert "estimated_bounty_rate_pct" not in refreshed.signal_tags
