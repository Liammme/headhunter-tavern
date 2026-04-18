from sqlalchemy.orm import Session

from app.models import Job, JobClaim


class ClaimJobNotFoundError(Exception):
    pass


def create_claim(db: Session, *, job_id: int, claimer_name: str) -> JobClaim:
    job = db.get(Job, job_id)
    if job is None:
        raise ClaimJobNotFoundError(job_id)

    claim = JobClaim(job_id=job_id, claimer_name=claimer_name.strip())
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
