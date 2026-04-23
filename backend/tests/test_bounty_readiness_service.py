from datetime import date, datetime

from app.models import Job
from app.services.bounty_readiness_service import audit_estimated_bounties


def build_job(*, company: str, title: str, days_ago: int, signal_tags: dict) -> Job:
    base_time = datetime(2026, 4, 23, 9, 0, 0)
    collected_at = base_time.replace(day=base_time.day - days_ago)
    return Job(
        canonical_url=f"https://jobs.example.com/{company.lower()}/{title.lower().replace(' ', '-')}",
        source_name="demo-board",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description="Build LLM platform and hiring roadmap.",
        posted_at=collected_at,
        collected_at=collected_at,
        bounty_grade="medium",
        signal_tags=signal_tags,
    )


def test_audit_estimated_bounties_counts_complete_partial_invalid_and_missing_rows(db_session):
    db_session.add_all(
        [
            build_job(
                company="OpenGradient",
                title="Principal AI Engineer",
                days_ago=0,
                signal_tags={
                    "estimated_bounty_amount": 150000,
                    "estimated_bounty_label": "¥120,000-¥180,000",
                    "estimated_bounty_min": 120000,
                    "estimated_bounty_max": 180000,
                    "estimated_bounty_rate_pct": 20,
                    "estimated_bounty_rule_version": "bounty-rule-v1",
                    "estimated_bounty_confidence": "medium",
                },
            ),
            build_job(
                company="OpenGradient",
                title="Growth Engineer",
                days_ago=0,
                signal_tags={
                    "estimated_bounty_amount": 24000,
                    "estimated_bounty_label": "¥19,200-¥28,800",
                },
            ),
            build_job(
                company="OpenGradient",
                title="Operations Coordinator",
                days_ago=0,
                signal_tags={
                    "estimated_bounty_amount": 24000,
                    "estimated_bounty_label": "¥19,200-¥28,800",
                    "estimated_bounty_min": 30000,
                    "estimated_bounty_max": 28000,
                    "estimated_bounty_rate_pct": 25,
                    "estimated_bounty_rule_version": "bounty-rule-v1",
                    "estimated_bounty_confidence": "medium",
                },
            ),
            build_job(
                company="Beta Labs",
                title="Backend Engineer",
                days_ago=0,
                signal_tags={"display_tags": ["技术"]},
            ),
        ]
    )
    db_session.commit()

    summary = audit_estimated_bounties(db_session, today=date(2026, 4, 23), window_days=14)

    assert summary["scanned_jobs"] == 4
    assert summary["complete_jobs"] == 1
    assert summary["partial_jobs"] == 1
    assert summary["invalid_jobs"] == 1
    assert summary["missing_jobs"] == 1
    assert summary["active_scanned_jobs"] == 4
    assert summary["active_complete_jobs"] == 1
    assert summary["active_partial_jobs"] == 1
    assert summary["active_invalid_jobs"] == 1
    assert summary["active_missing_jobs"] == 1
    assert summary["strict_readiness"] is False
    assert summary["issue_samples"]


def test_audit_estimated_bounties_reports_strict_readiness_when_active_rows_are_clean(db_session):
    db_session.add(
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            days_ago=0,
            signal_tags={
                "estimated_bounty_amount": 150000,
                "estimated_bounty_label": "¥120,000-¥180,000",
                "estimated_bounty_min": 120000,
                "estimated_bounty_max": 180000,
                "estimated_bounty_rate_pct": 20,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        )
    )
    db_session.commit()

    summary = audit_estimated_bounties(db_session, today=date(2026, 4, 23), window_days=14)

    assert summary["strict_readiness"] is True
    assert summary["active_partial_jobs"] == 0
    assert summary["active_invalid_jobs"] == 0
