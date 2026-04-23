from collections import defaultdict
from datetime import date, timedelta

from app.models import Job, JobClaim
from app.services.estimated_bounty_read import (
    PENDING_ESTIMATED_BOUNTY_LABEL,
    select_readable_estimated_bounty,
    should_expose_estimated_bounty,
)
from app.services.feed_snapshot import CompanyFeedSnapshot, DayBucketSnapshot, JobFeedSnapshot
from app.services.grouping import bucket_posted_date
from app.services.scoring import derive_company_grade

BUCKET_ORDER = {"today": 0, "yesterday": 1, "earlier": 2}
JOB_GRADE_ORDER = {"high": 0, "medium": 1, "low": 2}
COMPANY_GRADE_ORDER = {"focus": 0, "watch": 1, "normal": 2}
WINDOW_DAYS = 14


def build_claim_map(claims: list[JobClaim]) -> dict[int, list[str]]:
    claim_map: dict[int, list[str]] = defaultdict(list)
    for claim in claims:
        if claim.claimer_name not in claim_map[claim.job_id]:
            claim_map[claim.job_id].append(claim.claimer_name)
    return claim_map


def build_day_payloads(jobs: list[Job], claims: list[JobClaim], *, today: date) -> list[DayBucketSnapshot]:
    claim_map = build_claim_map(claims)
    window_start = today - timedelta(days=WINDOW_DAYS - 1)
    day_groups: dict[str, dict[str, dict]] = defaultdict(dict)

    for job in jobs:
        effective_date = (job.posted_at or job.collected_at).date()
        if effective_date < window_start:
            continue

        bucket = bucket_posted_date(effective_date, today)
        company_key = job.company_normalized or job.company
        company_group = day_groups[bucket].setdefault(
            company_key,
            {
                "company": job.company,
                "company_url": None,
                "jobs": [],
            },
        )
        if company_group["company_url"] is None:
            company_group["company_url"] = job.signal_tags.get("company_url")
        company_group["jobs"].append(job)

    day_payloads: list[DayBucketSnapshot] = []
    for bucket in sorted(day_groups.keys(), key=lambda item: BUCKET_ORDER[item]):
        companies: list[CompanyFeedSnapshot] = []
        for company in day_groups[bucket].values():
            sorted_jobs = sorted(
                company["jobs"],
                key=lambda current_job: (JOB_GRADE_ORDER[current_job.bounty_grade], current_job.title.lower()),
            )
            jobs_payload = [
                {
                    "id": job.id,
                    "title": job.title,
                    "canonical_url": job.canonical_url,
                    "bounty_grade": job.bounty_grade,
                    "tags": list(job.signal_tags.get("display_tags", [])),
                    "claimed_names": [],
                }
                for job in sorted_jobs
            ]
            company_claims: list[str] = []
            for job_item in jobs_payload:
                for name in claim_map.get(job_item["id"], []):
                    if name not in company_claims:
                        company_claims.append(name)
            company_grade = derive_company_grade([job_item["bounty_grade"] for job_item in jobs_payload])
            company_bounty_estimate = (
                _select_company_bounty_estimate(sorted_jobs) if _should_expose_estimated_bounty() else None
            )
            companies.append(
                CompanyFeedSnapshot(
                    company=company["company"],
                    company_url=company["company_url"],
                    company_grade=company_grade,
                    total_jobs=len(jobs_payload),
                    claimed_names=company_claims,
                    jobs=[JobFeedSnapshot(**job_item) for job_item in jobs_payload],
                    claimed_by=company_claims[0] if company_claims else None,
                    claim_status="claimed" if company_claims else None,
                    estimated_bounty_amount=company_bounty_estimate.amount if company_bounty_estimate else None,
                    estimated_bounty_label=company_bounty_estimate.label if company_bounty_estimate else PENDING_ESTIMATED_BOUNTY_LABEL,
                )
            )

        companies.sort(
            key=lambda item: (
                COMPANY_GRADE_ORDER[item.company_grade],
                JOB_GRADE_ORDER[item.jobs[0].bounty_grade],
                item.company.lower(),
            )
        )
        day_payloads.append(DayBucketSnapshot(bucket=bucket, companies=companies))

    return day_payloads


def _should_expose_estimated_bounty() -> bool:
    return should_expose_estimated_bounty()


def _select_company_bounty_estimate(jobs: list[Job]):
    return select_readable_estimated_bounty(jobs)
