from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crawlers.base import NormalizedJob
from app.crawlers.registry import ADAPTERS
from app.models import Job, JobClaim
from app.services.job_enrichment import build_job_payload

WINDOW_DAYS = 14


def run_crawl(db: Session) -> dict:
    _purge_demo_jobs(db)

    fetched_jobs: list[NormalizedJob] = []
    source_stats: dict[str, int] = {}
    errors: list[str] = []

    for source_name, adapter_cls in ADAPTERS.items():
        adapter = adapter_cls()
        try:
            jobs = adapter.fetch()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source_name}: {exc}")
            continue

        source_stats[source_name] = len(jobs)
        fetched_jobs.extend(jobs)

    new_jobs = upsert_jobs(db, fetched_jobs)
    return {
        "status": "triggered",
        "new_jobs": new_jobs,
        "fetched_jobs": len(fetched_jobs),
        "source_stats": source_stats,
        "errors": errors,
    }


def upsert_jobs(db: Session, fetched_jobs: Iterable[NormalizedJob]) -> int:
    unique_jobs: dict[str, NormalizedJob] = {}
    for job in fetched_jobs:
        canonical_url = (job.canonical_url or "").strip()
        title = (job.title or "").strip()
        if not canonical_url or not title:
            continue
        unique_jobs[canonical_url] = job

    existing_jobs = {
        item.canonical_url: item
        for item in db.execute(select(Job).where(Job.canonical_url.in_(list(unique_jobs.keys())))).scalars().all()
    }

    new_jobs = 0
    for canonical_url, normalized_job in unique_jobs.items():
        existing = existing_jobs.get(canonical_url)
        payload = build_job_payload(normalized_job)
        if existing is None:
            db.add(Job(**payload))
            new_jobs += 1
            continue

        for key, value in payload.items():
            setattr(existing, key, value)

    _delete_out_of_window_jobs(db)
    db.commit()
    return new_jobs
def _purge_demo_jobs(db: Session) -> None:
    demo_job_ids = db.execute(select(Job.id).where(Job.source_name == "demo")).scalars().all()
    if demo_job_ids:
        db.execute(delete(JobClaim).where(JobClaim.job_id.in_(demo_job_ids)))
        db.execute(delete(Job).where(Job.id.in_(demo_job_ids)))
        db.commit()


def _delete_out_of_window_jobs(db: Session) -> None:
    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS)
    stale_job_ids = db.execute(select(Job.id).where(Job.collected_at < cutoff)).scalars().all()
    if not stale_job_ids:
        return
    db.execute(delete(JobClaim).where(JobClaim.job_id.in_(stale_job_ids)))
    db.execute(delete(Job).where(Job.id.in_(stale_job_ids)))
