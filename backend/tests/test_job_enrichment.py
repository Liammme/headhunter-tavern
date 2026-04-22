from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob
from app.services.job_enrichment import build_job_payload, derive_company_name, enrich_job


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
    assert payload["bounty_grade"] == "medium"
    assert payload["signal_tags"]["display_tags"][0] == "AI"
    assert "job_facts" not in payload
    assert "score_inputs" not in payload
    assert "score_results" not in payload


def test_build_job_payload_preserves_company_url_when_present():
    job = NormalizedJob(
        source_job_id="with-company-url",
        canonical_url="https://jobs.example.com/opengradient/principal-ai-engineer",
        title="Principal AI Engineer",
        company="Open Gradient",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board", "company_url": " https://open-gradient.ai/company "},
    )

    payload = build_job_payload(job)

    assert payload["signal_tags"]["company_url"] == "https://open-gradient.ai/company"


def test_build_job_payload_does_not_guess_company_url_when_missing():
    job = NormalizedJob(
        source_job_id="without-company-url",
        canonical_url="https://jobs.example.com/opengradient/principal-ai-engineer",
        title="Principal AI Engineer",
        company="Open Gradient",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board"},
    )

    payload = build_job_payload(job)

    assert "company_url" not in payload["signal_tags"]


def test_enrich_job_exposes_parallel_v1_and_v2_results_for_internal_compare():
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

    enriched = enrich_job(job)

    assert enriched.v1_result.grade == "high"
    assert enriched.v2_result.rule_version == "score-v2"
    assert enriched.v2_result.grade in {"medium", "high"}
    assert enriched.v2_result.reasons
    assert enriched.v2_result.rule_hits
    assert enriched.payload["bounty_grade"] == enriched.v2_result.grade


def test_build_job_payload_uses_v2_grade_as_default_bounty_grade():
    job = NormalizedJob(
        source_job_id="founding-ai",
        canonical_url="https://open-gradient.ai/careers/principal-ai-engineer",
        title="Principal AI Engineer",
        company="Open Gradient",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board"},
    )

    enriched = enrich_job(job)
    payload = build_job_payload(job)

    assert enriched.v1_result.grade == "high"
    assert enriched.v2_result.grade == "medium"
    assert payload["bounty_grade"] == "medium"


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


def test_build_job_payload_marks_stale_non_senior_roles_without_crashing():
    job = NormalizedJob(
        source_job_id="backend-role",
        canonical_url="https://example.com/careers/backend-engineer",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build internal tools.",
        posted_at=datetime.now().replace(microsecond=0) - timedelta(days=8),
        raw_payload={},
    )

    payload = build_job_payload(job)

    assert payload["signal_tags"]["display_tags"][-1] == "长期挂岗"


def test_derive_company_name_falls_back_to_unknown_when_missing_host():
    assert derive_company_name("") == "Unknown Company"
