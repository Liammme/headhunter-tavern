from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, FeedMetadata, JobFeedSnapshot
from app.services.home_feed_assembler import assemble_home_payload
from app.schemas.home import HomePayload


def test_assemble_home_payload_serializes_feed_snapshots_without_changing_contract():
    day_payloads = [
        DayBucketSnapshot(
            bucket="within_3_days",
            companies=[
                CompanyFeedSnapshot(
                    company="OpenGradient",
                    company_url="https://example.com/company/opengradient",
                    company_grade="focus",
                    total_jobs=1,
                    claimed_names=["Liam"],
                    jobs=[
                        JobFeedSnapshot(
                            id=1,
                            title="Principal AI Engineer",
                            canonical_url="https://example.com/1",
                            bounty_grade="high",
                            tags=["AI", "Senior"],
                            claimed_names=["Liam"],
                            job_category="AI/算法",
                        )
                    ],
                )
            ],
        )
    ]

    payload = assemble_home_payload(
        intelligence={
            "narrative": "test",
            "headline": "test",
            "summary": "test",
            "analysis_version": "intelligence-v1",
            "rule_version": "rules-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
            "findings": [],
            "actions": [],
        },
        day_payloads=day_payloads,
        meta=FeedMetadata(
            analysis_version="feed-v1",
            rule_version="score-v1",
            window_start="2026-04-05",
            window_end="2026-04-18",
            generated_at="2026-04-18T09:00:00",
        ),
    )

    assert payload == {
        "intelligence": {
            "narrative": "test",
            "headline": "test",
            "summary": "test",
            "analysis_version": "intelligence-v1",
            "rule_version": "rules-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
            "findings": [],
            "actions": [],
        },
        "meta": {
            "analysis_version": "feed-v1",
            "rule_version": "score-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
        },
        "days": [
            {
                "bucket": "within_3_days",
                "companies": [
                    {
                        "company": "OpenGradient",
                        "company_url": "https://example.com/company/opengradient",
                        "company_grade": "focus",
                        "total_jobs": 1,
                        "claimed_names": ["Liam"],
                        "claimed_by": None,
                        "claim_status": None,
                        "estimated_bounty_amount": None,
                        "estimated_bounty_label": None,
                        "jd_trust": None,
                        "jobs": [
                            {
                                "id": 1,
                                "title": "Principal AI Engineer",
                                "canonical_url": "https://example.com/1",
                                "bounty_grade": "high",
                                "job_category": "AI/算法",
                                "tags": ["AI", "Senior"],
                                "claimed_names": ["Liam"],
                                "verification_tags": [],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    assert (
        HomePayload.model_validate(payload).model_dump()["days"][0]["companies"][0]["jobs"][0]["job_category"]
        == "AI/算法"
    )
