from app.services.job_facts import JobFacts, build_v1_score_input, build_v2_score_input
from app.services.scoring import score_job, score_job_v2


def test_build_comparison_snapshot_contains_readable_sections():
    from app.services.scoring_comparison import build_comparison_snapshot

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
    v1_input = build_v1_score_input(facts)
    v2_input = build_v2_score_input(facts)
    v1_result = score_job(v1_input)
    v2_result = score_job_v2(v2_input)

    snapshot = build_comparison_snapshot(
        facts=facts,
        v1_input=v1_input,
        v1_result=v1_result,
        v2_input=v2_input,
        v2_result=v2_result,
    )

    assert snapshot.title == "Principal AI Engineer"
    assert snapshot.facts["category"] == "AI/算法"
    assert snapshot.v1_input["critical"] is True
    assert snapshot.v1_result["grade"] == "high"
    assert snapshot.v2_input["seniority"] == "principal"
    assert snapshot.v2_result["rule_version"] == "score-v2"
    assert snapshot.summary["grade_changed"] is True


def test_comparison_snapshot_shows_v1_high_but_v2_medium_without_pressure():
    from app.services.scoring_comparison import build_comparison_snapshot

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

    snapshot = build_comparison_snapshot(
        facts=facts,
        v1_input=build_v1_score_input(facts),
        v1_result=score_job(build_v1_score_input(facts)),
        v2_input=build_v2_score_input(facts),
        v2_result=score_job_v2(build_v2_score_input(facts)),
    )

    assert snapshot.v1_result["grade"] == "high"
    assert snapshot.v2_result["grade"] == "medium"
    assert any("时间压力" in reason or "异常" in reason for reason in snapshot.summary["difference_notes"])


def test_comparison_snapshot_shows_v1_medium_but_v2_high_for_urgent_anomalous_role():
    from app.services.scoring_comparison import build_comparison_snapshot

    facts = JobFacts(
        title="Backend Engineer",
        category="技术",
        domain_tag="工具/SaaS",
        seniority="none",
        urgent=True,
        critical=False,
        bd_entry=False,
        hard_to_fill=False,
        role_complexity="medium",
        business_criticality="high",
        anomaly_signals=("long_running", "wish_list_jd"),
        compensation_signal="unknown",
        company_signal="neutral",
        time_pressure_signals=("urgent", "long_running"),
    )

    snapshot = build_comparison_snapshot(
        facts=facts,
        v1_input=build_v1_score_input(facts),
        v1_result=score_job(build_v1_score_input(facts)),
        v2_input=build_v2_score_input(facts),
        v2_result=score_job_v2(build_v2_score_input(facts)),
    )

    assert snapshot.v1_result["grade"] == "medium"
    assert snapshot.v2_result["grade"] == "high"
    assert "存在招聘异常或持续招不动信号" in snapshot.v2_result["reasons"]


def test_comparison_snapshot_shows_bd_entry_strength_even_without_core_rnd_bias():
    from app.services.scoring_comparison import build_comparison_snapshot

    facts = JobFacts(
        title="Business Development Manager",
        category="商务",
        domain_tag="Web3",
        seniority="senior",
        urgent=True,
        critical=False,
        bd_entry=True,
        hard_to_fill=False,
        role_complexity="medium",
        business_criticality="high",
        anomaly_signals=(),
        compensation_signal="unknown",
        company_signal="hot",
        time_pressure_signals=("urgent",),
    )

    snapshot = build_comparison_snapshot(
        facts=facts,
        v1_input=build_v1_score_input(facts),
        v1_result=score_job(build_v1_score_input(facts)),
        v2_input=build_v2_score_input(facts),
        v2_result=score_job_v2(build_v2_score_input(facts)),
    )

    assert snapshot.v1_result["grade"] == "medium"
    assert snapshot.v2_result["grade"] == "medium"
    assert any(hit["dimension"] == "bd_entry" for hit in snapshot.v2_result["rule_hits"])
