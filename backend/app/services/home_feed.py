from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobClaim
from app.services.feed_snapshot import build_feed_metadata
from app.services.home_feed_aggregation import build_day_payloads
from app.services.home_feed_assembler import assemble_home_payload
from app.services.intelligence import build_intelligence_snapshot


def build_home_payload(db: Session) -> dict:
    now = datetime.now().replace(microsecond=0)
    jobs = db.execute(select(Job)).scalars().all()
    claims = db.execute(select(JobClaim).order_by(JobClaim.created_at.asc(), JobClaim.id.asc())).scalars().all()
    day_payloads = build_day_payloads(jobs, claims, today=now.date())
    meta = build_feed_metadata(now, generated_at=_resolve_feed_generated_at(jobs, fallback=now))
    return assemble_home_payload(
        intelligence=build_intelligence_snapshot(day_payloads, meta, jobs=jobs),
        day_payloads=day_payloads,
        meta=meta,
    )


def _resolve_feed_generated_at(jobs: list[Job], *, fallback: datetime) -> datetime:
    latest_data_at = max(
        (job.collected_at or job.posted_at for job in jobs if job.collected_at or job.posted_at),
        default=None,
    )
    return (latest_data_at or fallback).replace(microsecond=0)
