from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawlers.registry import ADAPTERS, DISABLED_SOURCES
from app.services.company_contact_enrichment import (
    PublicWebsiteContactProvider,
    enrich_company_contacts,
)
from app.services.crawl_fetch_service import fetch_jobs
from app.services.crawl_run_lock import crawl_run_lock
from app.services.jdtrust_sidecar_trigger import trigger_jdtrust_sidecar_after_crawl
from app.services.job_upsert_service import purge_demo_jobs, upsert_jobs


def run_crawl(db: Session) -> dict:
    with crawl_run_lock(db):
        purge_demo_jobs(db)
        fetch_result = fetch_jobs(ADAPTERS)
        new_jobs = upsert_jobs(db, fetch_result.fetched_jobs)
        try:
            contact_enrichment = _run_contact_enrichment(db)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            contact_enrichment = {"status": "failed", "errors": [exc.__class__.__name__]}
        jdtrust_trigger = trigger_jdtrust_sidecar_after_crawl(new_jobs)

    source_health = dict(fetch_result.source_health)
    source_health.update({source_name: "disabled" for source_name in DISABLED_SOURCES})
    errors = list(fetch_result.errors)
    errors.extend(f"contact_enrichment: {error}" for error in contact_enrichment.get("errors", []))
    return {
        "status": "triggered",
        "new_jobs": new_jobs,
        "fetched_jobs": len(fetch_result.fetched_jobs),
        "source_stats": fetch_result.source_stats,
        "source_health": source_health,
        "disabled_sources": DISABLED_SOURCES,
        "errors": errors,
        "contact_enrichment": contact_enrichment,
        "jdtrust_trigger": jdtrust_trigger,
    }


def _run_contact_enrichment(db: Session) -> dict:
    if not settings.bounty_pool_contact_enrichment_enabled:
        return {"status": "disabled", "errors": []}
    provider = PublicWebsiteContactProvider(
        timeout_seconds=settings.bounty_pool_contact_enrichment_timeout_seconds,
    )
    return enrich_company_contacts(
        db,
        provider=provider,
        max_domains=settings.bounty_pool_contact_enrichment_max_domains,
        retry_after=timedelta(days=settings.bounty_pool_contact_enrichment_retry_days),
    )
