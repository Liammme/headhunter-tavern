from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, JobFeedSnapshot
from app.services.home_feed_assembler import assemble_home_payload


def test_assemble_home_payload_serializes_feed_snapshots_without_changing_contract():
    day_payloads = [
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
                            tags=["AI", "Senior"],
                            claimed_names=["Liam"],
                        )
                    ],
                )
            ],
        )
    ]

    payload = assemble_home_payload(
        intelligence={"headline": "test", "summary": "test", "findings": [], "actions": []},
        day_payloads=day_payloads,
    )

    assert payload == {
        "intelligence": {"headline": "test", "summary": "test", "findings": [], "actions": []},
        "days": [
            {
                "bucket": "today",
                "companies": [
                    {
                        "company": "OpenGradient",
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
