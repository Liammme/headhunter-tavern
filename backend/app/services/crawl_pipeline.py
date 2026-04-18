from sqlalchemy.orm import Session

from app.crawlers.base import NormalizedJob
from app.crawlers.registry import ADAPTERS
from app.services.job_upsert_service import purge_demo_jobs, upsert_jobs


def run_crawl(db: Session) -> dict:
    purge_demo_jobs(db)

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
