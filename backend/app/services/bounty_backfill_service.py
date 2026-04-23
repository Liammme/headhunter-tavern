from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import BountyEstimateInput, estimate_bounty
from app.services.job_facts import StandardizedJobInput, extract_job_facts


def backfill_estimated_bounties(db: Session) -> dict[str, int]:
    jobs = db.execute(select(Job).order_by(Job.id.asc())).scalars().all()
    updated_jobs = 0
    skipped_jobs = 0

    for job in jobs:
        signal_tags = dict(job.signal_tags or {})
        if _has_persisted_estimate(signal_tags):
            skipped_jobs += 1
            continue

        facts = extract_job_facts(_build_standardized_job_input(job), now=job.collected_at)
        estimate = estimate_bounty(_build_bounty_estimate_input(facts))
        signal_tags.update(
            {
                "estimated_bounty_amount": estimate.amount,
                "estimated_bounty_label": estimate.label,
                "estimated_bounty_min": estimate.min_amount,
                "estimated_bounty_max": estimate.max_amount,
                "estimated_bounty_rate_pct": estimate.rate_pct,
                "estimated_bounty_rule_version": estimate.rule_version,
                "estimated_bounty_confidence": estimate.confidence,
            }
        )
        job.signal_tags = signal_tags
        updated_jobs += 1

    db.commit()
    return {
        "scanned_jobs": len(jobs),
        "updated_jobs": updated_jobs,
        "skipped_jobs": skipped_jobs,
    }


def _has_persisted_estimate(signal_tags: dict) -> bool:
    return isinstance(signal_tags.get("estimated_bounty_amount"), int) and isinstance(
        signal_tags.get("estimated_bounty_label"), str
    )


def _build_standardized_job_input(job: Job) -> StandardizedJobInput:
    return StandardizedJobInput(
        canonical_url=job.canonical_url,
        source_name=job.source_name,
        title=job.title,
        company=job.company,
        company_normalized=job.company_normalized,
        description=job.description,
        posted_at=job.posted_at,
        collected_at=job.collected_at,
    )


def _build_bounty_estimate_input(facts) -> BountyEstimateInput:
    return BountyEstimateInput(
        category=facts.category,
        seniority=facts.seniority,
        domain_tag=facts.domain_tag,
        urgent=facts.urgent,
        critical=facts.critical,
        hard_to_fill=facts.hard_to_fill,
        role_complexity=facts.role_complexity,
        business_criticality=facts.business_criticality,
        compensation_signal=facts.compensation_signal,
        company_signal=facts.company_signal,
        time_pressure_signals=facts.time_pressure_signals,
    )
