from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crawlers.base import NormalizedJob
from app.models import Job, JobClaim
from app.services.bd_contact_service import mark_bd_contacts_stale_for_job_ids, refresh_bd_contacts_for_jobs
from app.services.job_enrichment import build_job_payload
from app.services.region import GLOBAL_REGION, RegionCode

WINDOW_DAYS = 30


def upsert_jobs(db: Session, fetched_jobs: Iterable[NormalizedJob], *, region: RegionCode = GLOBAL_REGION) -> int:
    unique_jobs: dict[str, NormalizedJob] = {}
    for job in fetched_jobs:
        canonical_url = (job.canonical_url or "").strip()
        title = (job.title or "").strip()
        if not canonical_url or not title:
            continue
        unique_jobs[canonical_url] = job

    existing_rows = db.execute(select(Job).where(Job.canonical_url.in_(list(unique_jobs.keys())))).scalars().all()
    existing_jobs = {item.canonical_url: item for item in existing_rows if item.region == region}
    cross_region_urls = {item.canonical_url for item in existing_rows if item.region != region}

    new_jobs = 0
    jobs_to_refresh_contacts: list[Job] = []
    for canonical_url, normalized_job in unique_jobs.items():
        if canonical_url in cross_region_urls:
            continue
        existing = existing_jobs.get(canonical_url)
        payload = build_job_payload(normalized_job)
        payload["region"] = region
        if existing is None:
            new_job = Job(**payload)
            db.add(new_job)
            jobs_to_refresh_contacts.append(new_job)
            new_jobs += 1
            continue

        for key, value in payload.items():
            setattr(existing, key, value)
        jobs_to_refresh_contacts.append(existing)

    db.flush()
    refresh_bd_contacts_for_jobs(db, jobs_to_refresh_contacts)
    delete_out_of_window_jobs(db, region=region)
    db.commit()
    return new_jobs


def purge_demo_jobs(db: Session) -> None:
    demo_job_ids = db.execute(select(Job.id).where(Job.source_name == "demo")).scalars().all()
    if demo_job_ids:
        db.execute(delete(JobClaim).where(JobClaim.job_id.in_(demo_job_ids)))
        db.execute(delete(Job).where(Job.id.in_(demo_job_ids)))
        db.commit()


def delete_out_of_window_jobs(db: Session, *, region: RegionCode = GLOBAL_REGION) -> None:
    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS)
    stale_job_ids = db.execute(select(Job.id).where(Job.collected_at < cutoff, Job.region == region)).scalars().all()
    if not stale_job_ids:
        return
    mark_bd_contacts_stale_for_job_ids(db, stale_job_ids)
    db.execute(delete(JobClaim).where(JobClaim.job_id.in_(stale_job_ids)))
    db.execute(delete(Job).where(Job.id.in_(stale_job_ids)))
