from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Job, JobClaim


class ClaimJobNotFoundError(Exception):
    pass


class ClaimCompanyAlreadyClaimedError(Exception):
    pass


def _normalize_company_key(job: Job) -> str:
    return (job.company_normalized or job.company or "").strip()


def create_claim(db: Session, *, job_id: int, claimer_name: str) -> JobClaim:
    job = db.get(Job, job_id)
    if job is None:
        raise ClaimJobNotFoundError(job_id)

    company_key = _normalize_company_key(job)
    company_name = (job.company or "").strip()
    company_matchers = []
    if job.company_normalized:
        company_matchers.append(Job.company_normalized == company_key)
    if company_name:
        company_matchers.append(Job.company == company_name)
    existing_claim = None
    if company_matchers:
        existing_claim = db.scalar(
            select(JobClaim.id)
            .join(Job, Job.id == JobClaim.job_id)
            .where(or_(*company_matchers))
            .limit(1)
        )
    if existing_claim is not None:
        raise ClaimCompanyAlreadyClaimedError(company_key)

    claim = JobClaim(job_id=job_id, claimer_name=claimer_name.strip())
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
