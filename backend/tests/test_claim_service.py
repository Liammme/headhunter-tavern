import pytest
from sqlalchemy import select

from app.models import Job, JobClaim
from app.services.claim_service import ClaimJobNotFoundError, create_claim


def build_job() -> Job:
    return Job(
        canonical_url="https://jobs.example.com/acme/founding-engineer",
        source_name="test",
        title="Founding Engineer",
        company="Acme",
        company_normalized="acme",
        description="Build the core platform.",
    )


def test_create_claim_persists_trimmed_name(db_session):
    job = build_job()
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    claim = create_claim(db_session, job_id=job.id, claimer_name="  Liam  ")
    stored_claims = db_session.execute(select(JobClaim)).scalars().all()

    assert claim.id is not None
    assert claim.job_id == job.id
    assert claim.claimer_name == "Liam"
    assert len(stored_claims) == 1
    assert stored_claims[0].claimer_name == "Liam"


def test_create_claim_raises_for_missing_job(db_session):
    with pytest.raises(ClaimJobNotFoundError):
        create_claim(db_session, job_id=999, claimer_name="Liam")
