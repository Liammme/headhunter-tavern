from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import BountyEstimate, build_bounty_estimate_input_from_facts, estimate_bounty
from app.services.job_facts import StandardizedJobInput, extract_job_facts


def backfill_estimated_bounties(db: Session) -> dict[str, int]:
    jobs = db.execute(select(Job).order_by(Job.id.asc())).scalars().all()
    updated_jobs = 0
    skipped_jobs = 0

    for job in jobs:
        signal_tags = dict(job.signal_tags or {})
        if BountyEstimate.from_signal_tags(signal_tags) is not None:
            skipped_jobs += 1
            continue

        facts = extract_job_facts(_build_standardized_job_input(job), now=job.collected_at)
        estimate = estimate_bounty(build_bounty_estimate_input_from_facts(facts))
        signal_tags.update(estimate.to_signal_tags())
        job.signal_tags = signal_tags
        updated_jobs += 1

    db.commit()
    return {
        "scanned_jobs": len(jobs),
        "updated_jobs": updated_jobs,
        "skipped_jobs": skipped_jobs,
    }


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
