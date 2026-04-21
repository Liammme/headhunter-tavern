from app.crawlers.base import NormalizedJob
from app.services.job_facts import (
    build_legacy_signal_tags,
    build_v1_score_input,
    build_v2_score_input,
    derive_company_name,
    extract_job_facts,
    standardize_job_input,
)
from app.services.scoring import RULE_VERSION_V2, score_job



def build_job_payload(job: NormalizedJob) -> dict:
    standardized = standardize_job_input(job)
    facts = extract_job_facts(standardized, now=standardized.collected_at)
    signal_tags = build_legacy_signal_tags(facts)
    v1_input = build_v1_score_input(facts)
    v2_input = build_v2_score_input(facts)
    bounty_grade = score_job(v1_input).grade

    return {
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
        "bounty_grade": bounty_grade,
        "signal_tags": signal_tags,
        "job_facts": {
            "category": facts.category,
            "domain_tag": facts.domain_tag,
            "seniority": facts.seniority,
            "urgent": facts.urgent,
            "critical": facts.critical,
            "bd_entry": facts.bd_entry,
            "hard_to_fill": facts.hard_to_fill,
            "role_complexity": facts.role_complexity,
            "business_criticality": facts.business_criticality,
            "anomaly_signals": list(facts.anomaly_signals),
            "compensation_signal": facts.compensation_signal,
            "company_signal": facts.company_signal,
            "time_pressure_signals": list(facts.time_pressure_signals),
        },
        "score_inputs": {
            "v1": {
                "title": v1_input.title,
                "category": v1_input.category,
                "urgent": v1_input.urgent,
                "critical": v1_input.critical,
                "bd_entry": v1_input.bd_entry,
            },
            "v2": {
                "rule_version": RULE_VERSION_V2,
                "seniority": v2_input.seniority,
                "urgent": v2_input.urgent,
                "critical": v2_input.critical,
                "bd_entry": v2_input.bd_entry,
                "hard_to_fill": v2_input.hard_to_fill,
                "role_complexity": v2_input.role_complexity,
                "business_criticality": v2_input.business_criticality,
                "anomaly_signals": list(v2_input.anomaly_signals),
                "category": v2_input.category,
                "domain_tag": v2_input.domain_tag,
                "compensation_signal": v2_input.compensation_signal,
                "company_signal": v2_input.company_signal,
                "time_pressure_signals": list(v2_input.time_pressure_signals),
            },
        },
    }
