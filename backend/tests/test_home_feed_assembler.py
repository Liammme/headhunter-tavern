from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, FeedMetadata, JobFeedSnapshot
from app.services.home_feed_assembler import assemble_home_payload


def test_assemble_home_payload_serializes_feed_snapshots_without_changing_contract():
    day_payloads = [
        DayBucketSnapshot(
            bucket="today",
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
                        )
                    ],
                )
            ],
        )
    ]

    payload = assemble_home_payload(
        intelligence={"narrative": "test", "headline": "test", "summary": "test", "findings": [], "actions": []},
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
        "intelligence": {"narrative": "test", "headline": "test", "summary": "test", "findings": [], "actions": []},
        "meta": {
            "analysis_version": "feed-v1",
            "rule_version": "score-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
        },
        "days": [
            {
                "bucket": "today",
                "companies": [
                    {
                        "company": "OpenGradient",
                        "company_url": "https://example.com/company/opengradient",
                        "company_grade": "focus",
                        "total_jobs": 1,
                        "claimed_names": ["Liam"],
                        "jobs": [
                            {
                                "id": 1,
                                "title": "Principal AI Engineer",
                                "canonical_url": "https://example.com/1",
                                "bounty_grade": "high",
                                "tags": ["AI", "Senior"],
                                "claimed_names": ["Liam"],
                            }
                        ],
                    }
                ],
            }
        ],
    }
