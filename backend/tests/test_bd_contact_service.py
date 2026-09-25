from datetime import datetime

from app.models import BdContact, Job
from app.services.bd_contact_service import (
    backfill_bd_contacts,
    mark_bd_contacts_stale_for_job_ids,
    refresh_bd_contacts_for_jobs,
)


def _add_job(db_session, *, description: str, region: str = "global") -> Job:
    job = Job(
        canonical_url=f"https://example.com/{region}/jobs/1",
        source_name="abetterweb3",
        region=region,
        title="BD Manager",
        company="Example",
        company_normalized="example",
        description=description,
        collected_at=datetime(2026, 6, 18, 9, 0, 0),
        signal_tags={"company_url": "https://example.com"},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_refresh_bd_contacts_for_jobs_upserts_contacts(db_session):
    job = _add_job(db_session, description="Contact TG: @HiringLead or hr@example.com")

    count = refresh_bd_contacts_for_jobs(db_session, [job])
    db_session.commit()

    contacts = db_session.query(BdContact).order_by(BdContact.contact_type).all()
    assert count == 3
    assert [(item.region, item.contact_type, item.contact_value, item.status) for item in contacts] == [
        ("global", "company_url", "https://example.com", "active"),
        ("global", "email", "hr@example.com", "active"),
        ("global", "telegram", "@hiringlead", "active"),
    ]


def test_refresh_bd_contacts_for_jobs_marks_missing_contacts_stale(db_session):
    job = _add_job(db_session, description="Contact hr@example.com")
    refresh_bd_contacts_for_jobs(db_session, [job])
    db_session.commit()

    job.description = "No direct contact now."
    refresh_bd_contacts_for_jobs(db_session, [job])
    db_session.commit()

    contacts = {item.contact_type: item for item in db_session.query(BdContact).all()}
    assert contacts["email"].status == "stale"
    assert contacts["company_url"].status == "active"


def test_refresh_bd_contacts_for_jobs_reuses_contact_left_by_deleted_job(db_session):
    old_job = _add_job(db_session, description="Contact hr@example.com")
    refresh_bd_contacts_for_jobs(db_session, [old_job])
    db_session.commit()

    old_url = old_job.canonical_url
    db_session.delete(old_job)
    db_session.commit()

    new_job = Job(
        canonical_url=old_url,
        source_name="abetterweb3",
        region="global",
        title="BD Manager",
        company="Example",
        company_normalized="example",
        description="Contact hr@example.com",
        collected_at=datetime(2026, 6, 19, 9, 0, 0),
        signal_tags={"company_url": "https://example.com"},
    )
    db_session.add(new_job)
    db_session.commit()

    count = refresh_bd_contacts_for_jobs(db_session, [new_job])
    db_session.commit()

    contacts = db_session.query(BdContact).order_by(BdContact.contact_type).all()
    assert count == 2
    assert len(contacts) == 2
    assert {item.job_id for item in contacts} == {new_job.id}
    assert {item.status for item in contacts} == {"active"}


def test_backfill_bd_contacts_filters_region(db_session):
    _add_job(db_session, description="Contact global@example.com", region="global")
    _add_job(db_session, description="Contact japan@example.com", region="japan")

    result = backfill_bd_contacts(db_session, region="japan")

    contacts = db_session.query(BdContact).all()
    assert result["jobs"] == 1
    assert [(item.region, item.contact_type, item.contact_value) for item in contacts] == [
        ("japan", "email", "japan@example.com"),
        ("japan", "company_url", "https://example.com"),
    ]


def test_mark_bd_contacts_stale_for_job_ids_only_updates_active_contacts(db_session):
    job = _add_job(db_session, description="Contact hr@example.com")
    refresh_bd_contacts_for_jobs(db_session, [job])
    db_session.commit()

    changed = mark_bd_contacts_stale_for_job_ids(db_session, [job.id])
    db_session.commit()

    contacts = db_session.query(BdContact).all()
    assert changed == 2
    assert {item.status for item in contacts} == {"stale"}


def test_refresh_bd_contacts_reads_verified_company_website_emails(db_session):
    job = _add_job(db_session, description="No direct contact in the job text.")
    job.signal_tags = {
        **job.signal_tags,
        "contact_enrichment": {
            "provider": "official_company_website",
            "status": "found",
            "checked_at": "2026-09-25T09:00:00",
            "emails": [
                {
                    "value": "hello@example.com",
                    "confidence": "high",
                    "evidence_url": "https://example.com/contact",
                }
            ],
        },
    }

    refresh_bd_contacts_for_jobs(db_session, [job])
    db_session.commit()

    email = db_session.query(BdContact).filter(BdContact.contact_type == "email").one()
    assert email.contact_value == "hello@example.com"
    assert email.evidence_snippet == "Official company website: https://example.com/contact"
