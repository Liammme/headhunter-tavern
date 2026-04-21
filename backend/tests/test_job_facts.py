from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob
from app.services.scoring import JobScoreInput, JobScoreV2Input


def test_extract_job_facts_recognizes_structured_signals_for_ai_lead_role():
    from app.services.job_facts import extract_job_facts, standardize_job_input

    job = NormalizedJob(
        source_job_id="ai-staff-role",
        canonical_url="https://open-gradient.ai/careers/staff-ai-engineer",
        title=" Staff AI Engineer ",
        company="",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description=(
            "Urgent hire for a founding AI platform lead. "
            "Own LLM roadmap, infra, product partnership, and customer delivery."
        ),
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board"},
    )

    standardized = standardize_job_input(job, now=datetime(2026, 4, 21, 9, 0, 0))
    facts = extract_job_facts(standardized, now=datetime(2026, 4, 21, 9, 0, 0))

    assert facts.title == "Staff AI Engineer"
    assert facts.category == "AI/算法"
    assert facts.domain_tag == "AI"
    assert facts.seniority == "staff"
    assert facts.urgent is True
    assert facts.critical is True
    assert facts.hard_to_fill is True
    assert facts.role_complexity == "high"
    assert facts.business_criticality == "high"
    assert "urgent" in facts.time_pressure_signals


def test_build_score_inputs_from_same_facts_supports_v1_and_v2():
    from app.services.job_facts import (
        build_v1_score_input,
        build_v2_score_input,
        extract_job_facts,
        standardize_job_input,
    )

    job = NormalizedJob(
        source_job_id="pm-role",
        canonical_url="https://growth-os.com/careers/senior-product-manager",
        title="Senior Product Manager",
        company="Growth OS",
        location="Shanghai",
        remote_type="hybrid",
        employment_type="full-time",
        description="Lead product roadmap, GTM coordination, and urgent launch delivery.",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={},
    )

    standardized = standardize_job_input(job, now=datetime(2026, 4, 21, 9, 0, 0))
    facts = extract_job_facts(standardized, now=datetime(2026, 4, 21, 9, 0, 0))

    assert build_v1_score_input(facts) == JobScoreInput(
        title="Senior Product Manager",
        category="产品",
        urgent=True,
        critical=False,
        bd_entry=True,
    )
    assert build_v2_score_input(facts) == JobScoreV2Input(
        seniority="senior",
        urgent=True,
        critical=False,
        bd_entry=True,
        hard_to_fill=False,
        role_complexity="medium",
        business_criticality="high",
        anomaly_signals=(),
        category="产品",
        domain_tag="工具/SaaS",
        compensation_signal="unknown",
        company_signal="neutral",
        time_pressure_signals=("urgent",),
    )


def test_extract_job_facts_marks_long_running_role_as_anomaly_without_fake_bd_entry():
    from app.services.job_facts import extract_job_facts, standardize_job_input

    job = NormalizedJob(
        source_job_id="backend-role",
        canonical_url="https://example.com/careers/backend-engineer",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build internal tools and platform services.",
        posted_at=datetime.now().replace(microsecond=0) - timedelta(days=10),
        raw_payload={},
    )

    standardized = standardize_job_input(job, now=datetime(2026, 4, 21, 9, 0, 0))
    facts = extract_job_facts(standardized, now=datetime(2026, 4, 21, 9, 0, 0))

    assert facts.bd_entry is False
    assert facts.urgent is False
    assert "long_running" in facts.anomaly_signals
    assert "long_running" in facts.time_pressure_signals
