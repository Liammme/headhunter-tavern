from __future__ import annotations

import csv
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BdContact

CSV_FIELDS = [
    "company",
    "job_title",
    "contact_type",
    "contact_value",
    "confidence",
    "region",
    "source_name",
    "job_url",
    "company_url",
    "evidence_snippet",
    "first_seen_at",
    "last_seen_at",
    "status",
]


def list_bd_contacts(
    db: Session,
    *,
    region: str,
    status: str = "active",
    contact_type: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[BdContact]:
    statement = select(BdContact).where(BdContact.region == region, BdContact.status == status)
    if contact_type:
        statement = statement.where(BdContact.contact_type == contact_type)
    statement = statement.order_by(BdContact.last_seen_at.desc(), BdContact.id.desc()).offset(offset).limit(limit)
    return list(db.execute(statement).scalars().all())


def serialize_bd_contact(contact: BdContact) -> dict:
    return {
        "id": contact.id,
        "company": contact.company,
        "companyNormalized": contact.company_normalized,
        "jobTitle": contact.job_title,
        "contactType": contact.contact_type,
        "contactValue": contact.contact_value,
        "confidence": contact.confidence,
        "region": contact.region,
        "sourceName": contact.source_name,
        "jobUrl": contact.job_url,
        "companyUrl": contact.company_url,
        "evidenceSnippet": contact.evidence_snippet,
        "firstSeenAt": contact.first_seen_at.isoformat(),
        "lastSeenAt": contact.last_seen_at.isoformat(),
        "status": contact.status,
    }


def build_bd_contacts_csv(contacts: list[BdContact]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for contact in contacts:
        writer.writerow(
            {
                "company": contact.company,
                "job_title": contact.job_title,
                "contact_type": contact.contact_type,
                "contact_value": contact.contact_value,
                "confidence": contact.confidence,
                "region": contact.region,
                "source_name": contact.source_name,
                "job_url": contact.job_url,
                "company_url": contact.company_url or "",
                "evidence_snippet": contact.evidence_snippet,
                "first_seen_at": contact.first_seen_at.isoformat(),
                "last_seen_at": contact.last_seen_at.isoformat(),
                "status": contact.status,
            }
        )
    return output.getvalue()
