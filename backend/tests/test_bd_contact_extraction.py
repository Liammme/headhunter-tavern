from datetime import datetime

from app.models import Job
from app.services.bd_contact_extraction import extract_bd_contact_candidates


def _job(description: str, *, source_name: str = "abetterweb3", signal_tags: dict | None = None) -> Job:
    return Job(
        canonical_url="https://example.com/jobs/1",
        source_name=source_name,
        region="global",
        title="BD Manager",
        company="Example",
        company_normalized="example",
        description=description,
        collected_at=datetime(2026, 6, 18, 9, 0, 0),
        signal_tags=signal_tags or {},
    )


def test_extract_bd_contacts_finds_common_contact_channels():
    job = _job(
        "Send CV to hr@example.com or product at sherlock dot xyz. "
        "TG: @HiringLead, WeChat: talent_bd_01, WhatsApp: +1 415 555 0199, "
        "Discord: hiring-team#1234."
    )

    contacts = extract_bd_contact_candidates(job)
    values = {(item.contact_type, item.contact_value) for item in contacts}

    assert ("email", "hr@example.com") in values
    assert ("email", "product@sherlock.xyz") in values
    assert ("telegram", "@hiringlead") in values
    assert ("wechat", "talent_bd_01") in values
    assert ("whatsapp", "+14155550199") in values
    assert ("discord", "hiring-team#1234") in values


def test_extract_bd_contacts_strips_wrapping_punctuation_from_emails():
    job = _job("Please send details to -lauren@example.com.")

    contacts = extract_bd_contact_candidates(job)

    assert [(item.contact_type, item.contact_value) for item in contacts] == [("email", "lauren@example.com")]


def test_extract_bd_contacts_keeps_unlabeled_web3_handles_as_social_handles():
    job = _job("Business Development Manager, remote, @CryptoRecruiter")

    contacts = extract_bd_contact_candidates(job)

    assert [(item.contact_type, item.contact_value, item.confidence) for item in contacts] == [
        ("social_handle", "@cryptorecruiter", "medium")
    ]


def test_extract_bd_contacts_adds_company_url_from_signal_tags():
    job = _job("No direct contact.", signal_tags={"company_url": "https://example.com/careers"})

    contacts = extract_bd_contact_candidates(job)

    assert [(item.contact_type, item.contact_value) for item in contacts] == [
        ("company_url", "https://example.com/careers")
    ]


def test_extract_bd_contacts_ignores_at_mentions_without_contact_context_for_japan_sources():
    job = _job("@cosme STORE sales role", source_name="mynavi_tenshoku")

    contacts = extract_bd_contact_candidates(job)

    assert contacts == []
