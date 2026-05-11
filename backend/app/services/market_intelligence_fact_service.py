from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.registry import ADAPTERS
from app.models import MarketIntelligenceFact
from app.services.market_intelligence_fact_extractor import extract_market_intelligence_fact

SUPPORTED_BACKFILL_DAYS = {30, 90, 180}


def backfill_market_intelligence_facts(
    db: Session,
    *,
    days: int,
    dry_run: bool = False,
    adapters: Iterable[SourceAdapter] | None = None,
    collected_at: datetime | None = None,
) -> dict:
    if days not in SUPPORTED_BACKFILL_DAYS:
        raise ValueError("days must be one of 30, 90, or 180")

    collected_at = (collected_at or datetime.now()).replace(microsecond=0)
    fetched_jobs, source_errors = _fetch_jobs(adapters)
    summary = {
        "days": days,
        "dry_run": dry_run,
        "fetched": len(fetched_jobs),
        "eligible": 0,
        "inserted": 0,
        "skipped_duplicate": 0,
        "skipped_out_of_window": 0,
        "skipped_invalid": 0,
        "skipped_source_errors": len(source_errors),
        "source_errors": source_errors,
    }

    extracted_facts = []
    for job in fetched_jobs:
        extracted = extract_market_intelligence_fact(job, collected_at=collected_at)
        if extracted is None:
            summary["skipped_invalid"] += 1
            continue
        if not _is_in_window(extracted.posted_at or extracted.collected_at, collected_at, days):
            summary["skipped_out_of_window"] += 1
            continue
        summary["eligible"] += 1
        extracted_facts.append(extracted)

    if not extracted_facts:
        return summary

    dedupe_keys = [fact.dedupe_key for fact in extracted_facts]
    existing_keys = set(
        db.execute(
            select(MarketIntelligenceFact.dedupe_key).where(MarketIntelligenceFact.dedupe_key.in_(dedupe_keys))
        )
        .scalars()
        .all()
    )

    seen_keys: set[str] = set()
    for fact in extracted_facts:
        if fact.dedupe_key in existing_keys or fact.dedupe_key in seen_keys:
            summary["skipped_duplicate"] += 1
            continue
        seen_keys.add(fact.dedupe_key)
        if dry_run:
            continue
        db.add(MarketIntelligenceFact(**fact.to_model_payload()))
        summary["inserted"] += 1

    if dry_run:
        return summary

    db.commit()
    return summary


def _fetch_jobs(adapters: Iterable[SourceAdapter] | None) -> tuple[list[NormalizedJob], list[dict]]:
    active_adapters = list(adapters) if adapters is not None else [adapter_class() for adapter_class in ADAPTERS.values()]
    jobs: list[NormalizedJob] = []
    source_errors: list[dict] = []
    for adapter in active_adapters:
        try:
            fetched = adapter.fetch()
        except Exception as exc:
            source_errors.append(
                {
                    "source": adapter.source_name,
                    "error": f"{type(exc).__name__}: {str(exc)}",
                }
            )
            continue
        for job in fetched:
            if isinstance(job.raw_payload, dict) and "site" not in job.raw_payload:
                job.raw_payload["site"] = adapter.source_name
            jobs.append(job)
    return jobs, source_errors


def _is_in_window(value: datetime, collected_at: datetime, days: int) -> bool:
    days_ago = (collected_at.date() - value.date()).days
    return 0 <= days_ago < days
