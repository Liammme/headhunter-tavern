from dataclasses import dataclass

from app.crawlers.base import NormalizedJob
from app.services.job_facts import (
    JobFacts,
    StandardizedJobInput,
    build_legacy_signal_tags,
    build_v1_score_input,
    build_v2_score_input,
    derive_company_name,
    extract_job_facts,
    standardize_job_input,
)
from app.services.scoring import (
    JobScoreInput,
    JobScoreResult,
    JobScoreV2Input,
    JobScoreV2Result,
    score_job,
    score_job_v2,
    select_primary_bounty_grade,
)


@dataclass(frozen=True)
class JobEnrichmentResult:
    standardized: StandardizedJobInput
    facts: JobFacts
    signal_tags: dict
    v1_input: JobScoreInput
    v2_input: JobScoreV2Input
    v1_result: JobScoreResult
    v2_result: JobScoreV2Result
    payload: dict


def enrich_job(job: NormalizedJob) -> JobEnrichmentResult:
    standardized = standardize_job_input(job)
    facts = extract_job_facts(standardized, now=standardized.collected_at)
    signal_tags = build_legacy_signal_tags(facts)
    company_url = extract_company_url(job)
    if company_url:
        signal_tags["company_url"] = company_url
    v1_input = build_v1_score_input(facts)
    v2_input = build_v2_score_input(facts)
    v1_result = score_job(v1_input)
    v2_result = score_job_v2(v2_input)
    payload = {
        "canonical_url": standardized.canonical_url,
        "source_name": standardized.source_name,
        "title": standardized.title,
        "company": standardized.company,
        "company_normalized": standardized.company_normalized,
        "description": standardized.description,
        "posted_at": standardized.posted_at,
        "collected_at": standardized.collected_at,
        "job_category": facts.category,
        "domain_tag": facts.domain_tag,
        "bounty_grade": select_primary_bounty_grade(v1_result, v2_result),
        "signal_tags": signal_tags,
    }
    return JobEnrichmentResult(
        standardized=standardized,
        facts=facts,
        signal_tags=signal_tags,
        v1_input=v1_input,
        v2_input=v2_input,
        v1_result=v1_result,
        v2_result=v2_result,
        payload=payload,
    )


def build_job_payload(job: NormalizedJob) -> dict:
    return enrich_job(job).payload


def extract_company_url(job: NormalizedJob) -> str | None:
    company_url = job.raw_payload.get("company_url")
    if not isinstance(company_url, str):
        return None

    normalized_url = company_url.strip()
    return normalized_url or None
