from app.services.scoring import (
    RULE_VERSION,
    RULE_VERSION_V2,
    JobScoreInput,
    JobScoreV2Input,
    JobScoreV2Result,
    ScoreRuleHit,
    derive_company_grade,
    score_job,
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
