from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobClaim
from app.core.config import settings
from app.services.feed_snapshot import build_feed_metadata
from app.services.home_feed_aggregation import build_day_payloads
from app.services.home_feed_assembler import assemble_home_payload
from app.services.intelligence import build_intelligence_snapshot
from app.services.jdtrust_assessment_read import load_jdtrust_assessments
from app.services.market_intelligence_read_service import load_latest_market_intelligence_for_home
from app.services.region import GLOBAL_REGION


def build_home_payload(db: Session) -> dict:
    now = datetime.now().replace(microsecond=0)
    jobs = db.execute(select(Job).where(Job.region == GLOBAL_REGION)).scalars().all()
    claims = _load_home_claims(db, jobs)
    day_payloads = build_day_payloads(
        jobs,
        claims,
        today=now.date(),
        jdtrust_assessments=_load_jdtrust_assessments(),
    )
    meta = build_feed_metadata(now, generated_at=_resolve_feed_generated_at(jobs, fallback=now))
    intelligence = load_latest_market_intelligence_for_home(db)
    if intelligence is None:
        intelligence = build_intelligence_snapshot(day_payloads, meta, jobs=jobs)
    return assemble_home_payload(
        intelligence=intelligence,
        day_payloads=day_payloads,
        meta=meta,
    )


def _load_home_claims(db: Session, jobs: list[Job]) -> list[JobClaim]:
    job_ids = [job.id for job in jobs if job.id is not None]
    if not job_ids:
        return []
    return (
        db.execute(
            select(JobClaim)
            .where(JobClaim.job_id.in_(job_ids))
            .order_by(JobClaim.created_at.asc(), JobClaim.id.asc())
        )
        .scalars()
        .all()
    )


def _resolve_feed_generated_at(jobs: list[Job], *, fallback: datetime) -> datetime:
    latest_data_at = max(
        (job.collected_at or job.posted_at for job in jobs if job.collected_at or job.posted_at),
        default=None,
    )
    return (latest_data_at or fallback).replace(microsecond=0)


def _load_jdtrust_assessments() -> dict[int, dict]:
    if not settings.bounty_pool_jdtrust_read_enabled:
        return {}
    return load_jdtrust_assessments(settings.bounty_pool_jdtrust_assessments_path)
