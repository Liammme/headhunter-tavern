from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.feed_snapshot import build_feed_metadata
from app.services.home_feed import _resolve_feed_generated_at
from app.services.home_feed_aggregation import build_day_payloads
from app.services.home_feed_assembler import assemble_home_payload
from app.services.intelligence import build_intelligence_snapshot
from app.services.market_intelligence_read_service import load_latest_market_intelligence_for_home
from app.services.region import GLOBAL_REGION, JAPAN_REGION, RegionCode, normalize_region


def build_region_home_payload(db: Session, region: RegionCode) -> dict:
    normalized_region = normalize_region(region)
    if normalized_region == GLOBAL_REGION:
        raise ValueError("Use build_home_payload for global home payloads")

    now = datetime.now().replace(microsecond=0)
    jobs = db.execute(select(Job).where(Job.region == normalized_region)).scalars().all()
    day_payloads = build_day_payloads(
        jobs,
        [],
        today=now.date(),
        jdtrust_assessments={},
        expose_claims=False,
        expose_estimated_bounty=False,
    )
    meta = build_feed_metadata(now, generated_at=_resolve_feed_generated_at(jobs, fallback=now))
    intelligence = load_latest_market_intelligence_for_home(db, region=normalized_region)
    if intelligence is None:
        intelligence = build_intelligence_snapshot(day_payloads, meta, jobs=jobs)
    return assemble_home_payload(
        intelligence=intelligence,
        day_payloads=day_payloads,
        meta=meta,
    )


def build_japan_home_payload(db: Session) -> dict:
    return build_region_home_payload(db, JAPAN_REGION)
