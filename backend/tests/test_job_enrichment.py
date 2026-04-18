from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob
from app.services.job_enrichment import build_job_payload, derive_company_name


def test_build_job_payload_derives_company_and_analysis_fields():
    job = NormalizedJob(
        source_job_id="founding-ai",
        canonical_url="https://open-gradient.ai/careers/principal-ai-engineer",
        title="  Principal AI Engineer  ",
        company="",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description=" Build LLM platform and hiring roadmap. ",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board"},
    )

    payload = build_job_payload(job)

    assert payload["company"] == "Open Gradient"
    assert payload["company_normalized"] == "open gradient"
    assert payload["source_name"] == "demo-board"
    assert payload["job_category"] == "AI/算法"
    assert payload["domain_tag"] == "AI"
    assert payload["bounty_grade"] == "high"
    assert payload["signal_tags"]["display_tags"][0] == "AI"


def test_build_job_payload_marks_stale_roles_as_long_running():
    job = NormalizedJob(
        source_job_id="ops-role",
        canonical_url="https://acme.ai/careers/senior-ai-engineer",
        title="Senior AI Engineer",
        company="Acme",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Support AI platform operations.",
        posted_at=datetime.now().replace(microsecond=0) - timedelta(days=8),
        raw_payload={},
    )

    payload = build_job_payload(job)

    assert payload["signal_tags"]["display_tags"][-1] == "长期挂岗"


def test_derive_company_name_falls_back_to_unknown_when_missing_host():
    assert derive_company_name("") == "Unknown Company"
