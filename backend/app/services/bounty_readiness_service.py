from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import classify_bounty_signal_tags
from app.services.estimated_bounty_read import select_readable_estimated_bounty

STATE_KEYS = ("complete", "partial", "invalid", "missing")
JOB_GRADE_ORDER = {"high": 0, "medium": 1, "low": 2}


def audit_estimated_bounties(db: Session, *, today: date, window_days: int) -> dict[str, object]:
    jobs = db.execute(select(Job).order_by(Job.id.asc())).scalars().all()
    window_start = today - timedelta(days=window_days - 1)
    totals = {state: 0 for state in STATE_KEYS}
    active_totals = {state: 0 for state in STATE_KEYS}
    active_company_groups: dict[str, list[Job]] = defaultdict(list)
    issue_samples: list[dict[str, object]] = []

    for job in jobs:
        state = classify_bounty_signal_tags(job.signal_tags if isinstance(job.signal_tags, dict) else None)
        totals[state] += 1
        effective_date = (job.posted_at or job.collected_at).date()
        if effective_date >= window_start:
            active_totals[state] += 1
            company_key = job.company_normalized or job.company
            active_company_groups[company_key].append(job)
            if state != "complete" and len(issue_samples) < 10:
                issue_samples.append(
                    {
                        "job_id": job.id,
                        "company": job.company,
                        "title": job.title,
                        "state": state,
                    }
                )

    active_companies_without_estimate = 0
    for jobs_in_company in active_company_groups.values():
        sorted_jobs = sorted(
            jobs_in_company,
            key=lambda current_job: (JOB_GRADE_ORDER.get(current_job.bounty_grade, 3), current_job.title.lower()),
        )
        if select_readable_estimated_bounty(sorted_jobs) is None:
            active_companies_without_estimate += 1

    return {
        "scanned_jobs": len(jobs),
        "complete_jobs": totals["complete"],
        "partial_jobs": totals["partial"],
        "invalid_jobs": totals["invalid"],
        "missing_jobs": totals["missing"],
        "active_scanned_jobs": sum(active_totals.values()),
        "active_complete_jobs": active_totals["complete"],
        "active_partial_jobs": active_totals["partial"],
        "active_invalid_jobs": active_totals["invalid"],
        "active_missing_jobs": active_totals["missing"],
        "active_companies_without_estimate": active_companies_without_estimate,
        "strict_readiness": active_totals["partial"] == 0 and active_totals["invalid"] == 0,
        "window_start": window_start.isoformat(),
        "window_end": today.isoformat(),
        "issue_samples": issue_samples,
    }
