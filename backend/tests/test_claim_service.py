import pytest
from sqlalchemy import select

from app.models import Job, JobClaim
from app.services.claim_service import (
    ClaimCompanyAlreadyClaimedError,
    ClaimJobNotFoundError,
    create_claim,
)


def build_job(
    *,
    canonical_url: str = "https://jobs.example.com/acme/founding-engineer",
    title: str = "Founding Engineer",
    company: str = "Acme",
    company_normalized: str = "acme",
) -> Job:
    return Job(
        canonical_url=canonical_url,
        source_name="test",
        title=title,
        company=company,
        company_normalized=company_normalized,
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


def test_create_claim_raises_when_company_already_claimed(db_session):
    first_job = build_job()
    second_job = build_job(
        canonical_url="https://jobs.example.com/acme/staff-engineer",
        title="Staff Engineer",
    )
    db_session.add_all([first_job, second_job])
    db_session.commit()
    db_session.refresh(first_job)
    db_session.refresh(second_job)

    create_claim(db_session, job_id=first_job.id, claimer_name="Liam")

    with pytest.raises(ClaimCompanyAlreadyClaimedError):
        create_claim(db_session, job_id=second_job.id, claimer_name="Mina")

    stored_claims = db_session.execute(select(JobClaim)).scalars().all()
    assert len(stored_claims) == 1
    assert stored_claims[0].job_id == first_job.id
