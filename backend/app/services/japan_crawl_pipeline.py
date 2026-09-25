from sqlalchemy.orm import Session

from app.crawlers.japan_registry import JAPAN_ADAPTERS
from app.services.crawl_fetch_service import fetch_jobs
from app.services.crawl_run_lock import crawl_run_lock
from app.services.job_upsert_service import upsert_jobs
from app.services.region import JAPAN_REGION


def run_japan_crawl(db: Session) -> dict:
    with crawl_run_lock(db):
        fetch_result = fetch_jobs(JAPAN_ADAPTERS)
        new_jobs = upsert_jobs(db, fetch_result.fetched_jobs, region=JAPAN_REGION)
    return {
        "status": "completed",
        "region": JAPAN_REGION,
        "new_jobs": new_jobs,
        "fetched_jobs": len(fetch_result.fetched_jobs),
        "source_stats": fetch_result.source_stats,
        "source_health": fetch_result.source_health,
        "errors": fetch_result.errors,
        "jdtrust_trigger": {"status": "skipped_by_region_policy"},
    }
