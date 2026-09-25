from datetime import datetime

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.services.crawl_fetch_service import fetch_jobs


class SuccessAdapter(SourceAdapter):
    source_name = "success"

    def fetch(self) -> list[NormalizedJob]:
        now = datetime(2026, 4, 18, 9, 0, 0)
        return [
            NormalizedJob(
                source_job_id="1",
                canonical_url="https://example.com/1",
                title="Engineer",
                company="Acme",
                location="Remote",
                remote_type="remote",
                employment_type="full-time",
                description="test",
                posted_at=now,
                raw_payload={},
            )
        ]


class FailingAdapter(SourceAdapter):
    source_name = "failing"

    def fetch(self) -> list[NormalizedJob]:
        raise RuntimeError("boom")


class EmptyAdapter(SourceAdapter):
    source_name = "empty"

    def fetch(self) -> list[NormalizedJob]:
        return []


def test_fetch_jobs_collects_stats_jobs_and_errors():
    result = fetch_jobs(
        {
            "success": SuccessAdapter,
            "empty": EmptyAdapter,
            "failing": FailingAdapter,
        }
    )

    assert len(result.fetched_jobs) == 1
    assert result.source_stats == {"success": 1, "empty": 0, "failing": 0}
    assert result.source_health == {
        "success": "ok",
        "empty": "empty",
        "failing": "error",
    }
    assert result.errors == ["failing: boom"]
