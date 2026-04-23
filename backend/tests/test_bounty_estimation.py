from app.services.bounty_estimation import BountyEstimateInput, estimate_bounty


def test_estimate_bounty_returns_high_end_range_for_ai_principal():
    estimate = estimate_bounty(
        BountyEstimateInput(
            category="AI/算法",
            seniority="principal",
            domain_tag="AI",
            urgent=True,
            critical=True,
            hard_to_fill=True,
            role_complexity="high",
            business_criticality="high",
            compensation_signal="unknown",
            company_signal="hot",
            time_pressure_signals=("urgent", "long_running"),
        )
    )

    assert estimate.amount == 150000
    assert estimate.min_amount == 120000
    assert estimate.max_amount == 180000
    assert estimate.rate_pct == 20
    assert estimate.label == "¥120,000-¥180,000"
    assert estimate.rule_version == "bounty-rule-v1"


def test_estimate_bounty_keeps_low_complexity_ops_roles_near_floor():
    estimate = estimate_bounty(
        BountyEstimateInput(
            category="运营",
            seniority="none",
            domain_tag="工具/SaaS",
            urgent=False,
            critical=False,
            hard_to_fill=False,
            role_complexity="low",
            business_criticality="low",
            compensation_signal="unknown",
            company_signal="neutral",
            time_pressure_signals=(),
        )
    )

    assert estimate.amount == 24000
    assert estimate.min_amount == 19200
    assert estimate.max_amount == 28800
    assert estimate.rate_pct == 12
    assert estimate.label == "¥19,200-¥28,800"
