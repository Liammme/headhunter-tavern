from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crawlers.base import NormalizedJob
from app.models import Job, JobClaim
from app.services.job_enrichment import build_job_payload

WINDOW_DAYS = 14


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

    delete_out_of_window_jobs(db)
    db.commit()
    return new_jobs


def purge_demo_jobs(db: Session) -> None:
    demo_job_ids = db.execute(select(Job.id).where(Job.source_name == "demo")).scalars().all()
    if demo_job_ids:
        db.execute(delete(JobClaim).where(JobClaim.job_id.in_(demo_job_ids)))
        db.execute(delete(Job).where(Job.id.in_(demo_job_ids)))
        db.commit()


def delete_out_of_window_jobs(db: Session) -> None:
    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS)
    stale_job_ids = db.execute(select(Job.id).where(Job.collected_at < cutoff)).scalars().all()
    if not stale_job_ids:
        return
    db.execute(delete(JobClaim).where(JobClaim.job_id.in_(stale_job_ids)))
    db.execute(delete(Job).where(Job.id.in_(stale_job_ids)))
