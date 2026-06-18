from __future__ import annotations

from datetime import datetime
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BdContact, Job
from app.services.bd_contact_extraction import BdContactCandidate, extract_bd_contact_candidates


def backfill_bd_contacts(db: Session, *, region: str | None = None) -> dict:
    statement = select(Job)
    if region:
        statement = statement.where(Job.region == region)
    jobs = list(db.execute(statement).scalars().all())
    changed = refresh_bd_contacts_for_jobs(db, jobs)
    db.commit()
    return {"jobs": len(jobs), "changed_contacts": changed}


def refresh_bd_contacts_for_jobs(db: Session, jobs: list[Job]) -> int:
    changed = 0
    for job in jobs:
        changed += refresh_bd_contacts_for_job(db, job)
    return changed


def refresh_bd_contacts_for_job(db: Session, job: Job) -> int:
    candidates = extract_bd_contact_candidates(job)
    existing_contacts = db.execute(select(BdContact).where(BdContact.job_id == job.id)).scalars().all()
    existing_by_key = {contact.dedupe_key: contact for contact in existing_contacts}
    active_keys: set[str] = set()
    now = datetime.now()
    changed = 0

    for candidate in candidates:
        dedupe_key = _dedupe_key(job, candidate)
        active_keys.add(dedupe_key)
        existing = existing_by_key.get(dedupe_key)
        if existing is None:
            db.add(_build_contact(job, candidate, dedupe_key=dedupe_key, now=now))
            changed += 1
            continue

        existing.confidence = candidate.confidence
        existing.evidence_snippet = candidate.evidence_snippet
        existing.status = "active"
        existing.last_seen_at = now
        existing.updated_at = now
        changed += 1

    for contact in existing_contacts:
        if contact.dedupe_key in active_keys or contact.status != "active":
            continue
        contact.status = "stale"
        contact.updated_at = now
        changed += 1

    return changed


def mark_bd_contacts_stale_for_job_ids(db: Session, job_ids: list[int]) -> int:
    if not job_ids:
        return 0
    contacts = db.execute(
        select(BdContact).where(BdContact.job_id.in_(job_ids), BdContact.status == "active")
    ).scalars().all()
    now = datetime.now()
    for contact in contacts:
        contact.status = "stale"
        contact.updated_at = now
    return len(contacts)


def _build_contact(job: Job, candidate: BdContactCandidate, *, dedupe_key: str, now: datetime) -> BdContact:
    company_url = _company_url(job)
    return BdContact(
        dedupe_key=dedupe_key,
        job_id=job.id,
        region=job.region,
        company=job.company,
        company_normalized=job.company_normalized,
        job_title=job.title,
        contact_type=candidate.contact_type,
        contact_value=candidate.contact_value,
        normalized_value=_normalized_value(candidate),
        confidence=candidate.confidence,
        source_name=job.source_name,
        job_url=job.canonical_url,
        company_url=company_url,
        evidence_snippet=candidate.evidence_snippet,
        status="active",
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )


def _dedupe_key(job: Job, candidate: BdContactCandidate) -> str:
    raw = "|".join(
        [
            job.region or "",
            job.canonical_url or "",
            candidate.contact_type,
            _normalized_value(candidate),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalized_value(candidate: BdContactCandidate) -> str:
    if candidate.contact_type in {"email", "telegram", "social_handle", "wechat", "discord"}:
        return candidate.contact_value.strip().lower()
    if candidate.contact_type in {"phone", "whatsapp"}:
        prefix = "+" if candidate.contact_value.strip().startswith("+") else ""
        digits = "".join(ch for ch in candidate.contact_value if ch.isdigit())
        return f"{prefix}{digits}"
    return candidate.contact_value.strip()


def _company_url(job: Job) -> str | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    value = signal_tags.get("company_url")
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value.lower().startswith(("http://", "https://")) else None
