from datetime import datetime, timedelta

from sqlalchemy import select

from app.crawlers.base import NormalizedJob
from app.models import Job, JobClaim
from app.services import job_upsert_service
from app.services.job_upsert_service import delete_out_of_window_jobs, purge_demo_jobs, upsert_jobs


def build_normalized_job(*, canonical_url: str, title: str, company: str, description: str) -> NormalizedJob:
    return NormalizedJob(
        source_job_id=canonical_url,
        canonical_url=canonical_url,
        title=title,
        company=company,
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description=description,
        posted_at=datetime(2026, 4, 18, 9, 0, 0),
        raw_payload={"site": "test-board"},
    )


def test_upsert_jobs_deduplicates_by_canonical_url_and_updates_existing(db_session):
    existing = Job(
        canonical_url="https://jobs.example.com/acme/founding-engineer",
        source_name="old",
        title="Old title",
        company="Acme",
        company_normalized="acme",
        description="old description",
        collected_at=datetime.now().replace(microsecond=0),
    )
    db_session.add(existing)
    db_session.commit()

    new_jobs = upsert_jobs(
        db_session,
        [
            build_normalized_job(
                canonical_url="https://jobs.example.com/acme/founding-engineer",
                title="Founding Engineer",
                company="Acme",
                description="first payload",
            ),
            build_normalized_job(
                canonical_url="https://jobs.example.com/acme/founding-engineer",
                title="Principal Engineer",
                company="Acme",
                description="latest payload wins",
            ),
            build_normalized_job(
                canonical_url="https://jobs.example.com/beta/product-manager",
                title="Product Manager",
                company="Beta",
                description="new job",
            ),
        ],
    )

    jobs = db_session.execute(select(Job).order_by(Job.canonical_url.asc())).scalars().all()

    assert new_jobs == 1
    assert len(jobs) == 2
    assert jobs[0].title == "Principal Engineer"
    assert jobs[0].description == "latest payload wins"


def test_upsert_jobs_persists_long_titles(db_session):
    long_title = "Principal AI Platform Engineer " * 30
    expected_title = long_title.strip()

    new_jobs = upsert_jobs(
        db_session,
        [
            build_normalized_job(
                canonical_url="https://jobs.example.com/acme/principal-ai-platform-engineer",
                title=long_title,
                company="Acme",
                description="long title payload",
            )
        ],
    )

    stored_job = db_session.execute(select(Job)).scalars().one()

    assert new_jobs == 1
    assert stored_job.title == expected_title


def test_purge_demo_jobs_removes_demo_jobs_and_claims(db_session):
    demo_job = Job(
        canonical_url="https://jobs.example.com/demo/demo-role",
        source_name="demo",
        title="Demo Role",
        company="Demo",
        company_normalized="demo",
        description="demo",
        collected_at=datetime.now().replace(microsecond=0),
    )
    stale_claim = JobClaim(job_id=1, claimer_name="Liam")
    db_session.add(demo_job)
    db_session.commit()
    stale_claim.job_id = demo_job.id
    db_session.add(stale_claim)
    db_session.commit()

    purge_demo_jobs(db_session)

    assert db_session.execute(select(Job)).scalars().all() == []
    assert db_session.execute(select(JobClaim)).scalars().all() == []


def test_delete_out_of_window_jobs_keeps_jobs_collected_within_30_days(db_session, monkeypatch):
    fixed_now = datetime(2026, 4, 26, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(job_upsert_service, "datetime", FrozenDateTime)

    stale_job = Job(
        canonical_url="https://jobs.example.com/acme/stale-role",
        source_name="test",
        title="Stale Role",
        company="Acme",
        company_normalized="acme",
        description="stale",
        collected_at=fixed_now - timedelta(days=31),
    )
    fresh_job = Job(
        canonical_url="https://jobs.example.com/acme/fresh-role",
        source_name="test",
        title="Fresh Role",
        company="Acme",
        company_normalized="acme",
        description="fresh",
        collected_at=fixed_now - timedelta(days=29),
    )
    boundary_job = Job(
        canonical_url="https://jobs.example.com/acme/boundary-role",
        source_name="test",
        title="Boundary Role",
        company="Acme",
        company_normalized="acme",
        description="boundary",
        collected_at=fixed_now - timedelta(days=30),
    )
    db_session.add_all([stale_job, fresh_job, boundary_job])
    db_session.commit()

    stale_claim = JobClaim(job_id=stale_job.id, claimer_name="Liam")
    fresh_claim = JobClaim(job_id=fresh_job.id, claimer_name="Mia")
    boundary_claim = JobClaim(job_id=boundary_job.id, claimer_name="Noah")
    db_session.add_all([stale_claim, fresh_claim, boundary_claim])
    db_session.commit()
    fresh_job_url = fresh_job.canonical_url
    fresh_job_id = fresh_job.id
    boundary_job_url = boundary_job.canonical_url
    boundary_job_id = boundary_job.id

    delete_out_of_window_jobs(db_session)

    remaining_jobs = db_session.execute(select(Job).order_by(Job.canonical_url.asc())).scalars().all()
    remaining_claims = db_session.execute(select(JobClaim).order_by(JobClaim.claimer_name.asc())).scalars().all()

    assert [job.canonical_url for job in remaining_jobs] == [boundary_job_url, fresh_job_url]
    assert [claim.job_id for claim in remaining_claims] == [fresh_job_id, boundary_job_id]


def test_upsert_jobs_flushes_existing_job_updates_before_retention_cleanup(db_session, monkeypatch):
    fixed_now = datetime(2026, 4, 26, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(job_upsert_service, "datetime", FrozenDateTime)

    existing = Job(
        canonical_url="https://jobs.example.com/acme/senior-engineer",
        source_name="old",
        title="Old title",
        company="Acme",
        company_normalized="acme",
        description="old description",
        collected_at=fixed_now - timedelta(days=31),
    )
    db_session.add(existing)
    db_session.commit()

    claim = JobClaim(job_id=existing.id, claimer_name="Liam")
    db_session.add(claim)
    db_session.commit()

    new_jobs = upsert_jobs(
        db_session,
        [
            build_normalized_job(
                canonical_url=existing.canonical_url,
                title="Senior Engineer",
                company="Acme",
                description="fresh description",
            )
        ],
    )

    stored_job = db_session.execute(select(Job)).scalars().one()
    stored_claim = db_session.execute(select(JobClaim)).scalars().one()

    assert new_jobs == 0
    assert stored_job.title == "Senior Engineer"
    assert stored_job.description == "fresh description"
    assert stored_job.collected_at >= fixed_now - timedelta(days=30)
    assert stored_claim.job_id == stored_job.id
