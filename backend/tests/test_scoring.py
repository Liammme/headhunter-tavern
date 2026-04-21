from app.services.scoring import (
    DEFAULT_BOUNTY_RULE_VERSION,
    RULE_VERSION,
    RULE_VERSION_V2,
    JobScoreInput,
    JobScoreV2Input,
    JobScoreV2Result,
    ScoreRuleHit,
    derive_company_grade,
    select_primary_bounty_grade,
    score_job,
    score_job_v2,
)


def test_score_job_returns_structured_result():
    score = score_job(
        JobScoreInput(
            title="Principal AI Engineer",
            category="AI/算法",
            urgent=True,
            critical=True,
            bd_entry=False,
        )
    )

    assert score.score == 8
    assert score.grade == "high"


def test_score_job_handles_bd_entry_without_high_grade():
    score = score_job(
        JobScoreInput(
            title="Growth Manager",
            category="增长",
            urgent=False,
            critical=False,
            bd_entry=True,
        )
    )

    assert score.score == 1
    assert score.grade == "low"


def test_derive_company_grade_keeps_existing_tie_behavior():
    assert derive_company_grade(["high", "medium"]) == "watch"


def test_v2_input_captures_structured_fact_fields():
    facts = JobScoreV2Input(
        seniority="staff",
        urgent=True,
        critical=True,
        bd_entry=False,
        hard_to_fill=True,
        role_complexity="cross_functional",
        business_criticality="revenue_core",
        anomaly_signals=("reposted", "wish_list_jd"),
        category="AI/算法",
        domain_tag="AI",
        compensation_signal="strong",
        company_signal="hot",
        time_pressure_signals=("urgent", "fast_process"),
    )

    assert facts.seniority == "staff"
    assert facts.anomaly_signals == ("reposted", "wish_list_jd")
    assert facts.time_pressure_signals == ("urgent", "fast_process")


def test_v2_result_carries_version_reasons_and_rule_hits():
    result = JobScoreV2Result(
        score=83,
        grade="high",
        rule_version=RULE_VERSION_V2,
        reasons=("急招且重复发布", "核心 AI 岗位", "可作为 BD 切入口"),
        rule_hits=(
            ScoreRuleHit(code="time_pressure.urgent", dimension="time_pressure", weight=22),
            ScoreRuleHit(code="bd_entry.product", dimension="bd_entry", weight=10),
        ),
    )

    assert RULE_VERSION == "score-v1"
    assert result.rule_version == "score-v2"
    assert result.rule_hits[0].dimension == "time_pressure"


def test_default_bounty_rule_switches_to_v2_with_v1_fallback_kept():
    v1_result = score_job(
        JobScoreInput(
            title="Principal AI Engineer",
            category="AI/算法",
            urgent=False,
            critical=True,
            bd_entry=False,
        )
    )
    v2_result = score_job_v2(
        JobScoreV2Input(
            seniority="principal",
            urgent=False,
            critical=True,
            bd_entry=False,
            hard_to_fill=True,
            role_complexity="high",
            business_criticality="medium",
            anomaly_signals=(),
            category="AI/算法",
            domain_tag="AI",
            compensation_signal="unknown",
            company_signal="hot",
            time_pressure_signals=(),
        )
    )

    assert DEFAULT_BOUNTY_RULE_VERSION == "score-v2"
    assert select_primary_bounty_grade(v1_result, v2_result) == "medium"


def test_score_job_v2_returns_high_for_urgent_hard_to_fill_core_role():
    result = score_job_v2(
        JobScoreV2Input(
            seniority="staff",
            urgent=True,
            critical=True,
            bd_entry=False,
            hard_to_fill=True,
            role_complexity="high",
            business_criticality="high",
            anomaly_signals=("wish_list_jd",),
            category="AI/算法",
            domain_tag="AI",
            compensation_signal="strong",
            company_signal="hot",
            time_pressure_signals=("urgent", "founder_hiring"),
        )
    )

    assert result.rule_version == "score-v2"
    assert result.grade == "high"
    assert result.score >= 75
    assert result.reasons
    assert any(hit.dimension == "time_pressure" for hit in result.rule_hits)


def test_score_job_v2_returns_medium_for_bd_entry_role_with_some_pressure():
    result = score_job_v2(
        JobScoreV2Input(
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
    )

    assert result.grade == "medium"
    assert 45 <= result.score < 75
    assert any(hit.dimension == "bd_entry" for hit in result.rule_hits)


def test_score_job_v2_returns_low_for_low_pressure_general_role():
    result = score_job_v2(
        JobScoreV2Input(
            seniority="none",
            urgent=False,
            critical=False,
            bd_entry=False,
            hard_to_fill=False,
            role_complexity="low",
            business_criticality="low",
            anomaly_signals=(),
            category="运营",
            domain_tag="工具/SaaS",
            compensation_signal="unknown",
            company_signal="neutral",
            time_pressure_signals=(),
        )
    )

    assert result.grade == "low"
    assert result.score < 45
    assert all(hit.dimension != "bd_entry" for hit in result.rule_hits)


def test_v2_downgrades_high_keyword_role_without_pressure_or_anomaly():
    from app.services.job_facts import JobFacts, build_v1_score_input, build_v2_score_input

    facts = JobFacts(
        title="Principal AI Engineer",
        category="AI/算法",
        domain_tag="AI",
        seniority="principal",
        urgent=False,
        critical=True,
        bd_entry=False,
        hard_to_fill=True,
        role_complexity="high",
        business_criticality="medium",
        anomaly_signals=(),
        compensation_signal="unknown",
        company_signal="hot",
        time_pressure_signals=(),
    )

    v1_result = score_job(build_v1_score_input(facts))
    v2_result = score_job_v2(build_v2_score_input(facts))

    assert v1_result.grade == "high"
    assert v2_result.grade == "medium"
