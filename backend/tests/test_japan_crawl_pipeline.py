from datetime import datetime

from sqlalchemy import select

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.models import Job
from app.services.region import JAPAN_REGION


class FakeJapanAdapter(SourceAdapter):
    source_name = "fake_japan"

    def fetch(self) -> list[NormalizedJob]:
        now = datetime.now().replace(microsecond=0)
        return [
            NormalizedJob(
                source_job_id="jp-1",
                canonical_url="https://jobs.example.jp/company/japan-engineer",
                title="Japan Platform Engineer",
                company="Tokyo Signal",
                location="Tokyo",
                remote_type="hybrid",
                employment_type="full-time",
                description="Build hiring intelligence products for Japan.",
                posted_at=now,
                raw_payload={},
            )
        ]


def test_japan_crawl_uses_japan_adapters_and_writes_japan_region(db_session, monkeypatch):
    from app.services import japan_crawl_pipeline

    monkeypatch.setattr(japan_crawl_pipeline, "JAPAN_ADAPTERS", {"fake_japan": FakeJapanAdapter})

    summary = japan_crawl_pipeline.run_japan_crawl(db_session)

    jobs = db_session.execute(select(Job)).scalars().all()
    assert summary["status"] == "completed"
    assert summary["region"] == JAPAN_REGION
    assert summary["new_jobs"] == 1
    assert summary["fetched_jobs"] == 1
    assert summary["source_stats"] == {"fake_japan": 1}
    assert len(jobs) == 1
    assert jobs[0].region == JAPAN_REGION


def test_japan_crawl_does_not_trigger_jdtrust_sidecar(db_session, monkeypatch):
    from app.services import japan_crawl_pipeline

    monkeypatch.setattr(japan_crawl_pipeline, "JAPAN_ADAPTERS", {"fake_japan": FakeJapanAdapter})
    trigger_calls = []

    def fake_trigger(new_jobs):
        trigger_calls.append(new_jobs)
        return {"status": "started"}

    monkeypatch.setattr("app.services.crawl_pipeline.trigger_jdtrust_sidecar_after_crawl", fake_trigger)

    summary = japan_crawl_pipeline.run_japan_crawl(db_session)

    assert summary["jdtrust_trigger"] == {"status": "skipped_by_region_policy"}
    assert trigger_calls == []
