from sqlalchemy.orm import Session

from app.crawlers.registry import ADAPTERS
from app.services.crawl_fetch_service import fetch_jobs
from app.services.job_upsert_service import purge_demo_jobs, upsert_jobs


def run_crawl(db: Session) -> dict:
    purge_demo_jobs(db)
    fetch_result = fetch_jobs(ADAPTERS)
    new_jobs = upsert_jobs(db, fetch_result.fetched_jobs)
    return {
        "status": "triggered",
        "new_jobs": new_jobs,
        "fetched_jobs": len(fetch_result.fetched_jobs),
        "source_stats": fetch_result.source_stats,
        "errors": fetch_result.errors,
    }
