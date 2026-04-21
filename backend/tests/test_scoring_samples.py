def test_build_scoring_sample_suite_returns_fixed_readable_cases():
    from app.services.scoring_samples import build_scoring_sample_suite

    samples = build_scoring_sample_suite()

    assert [sample.sample_id for sample in samples] == [
        "principal-ai-no-pressure",
        "urgent-backend-anomaly",
        "bd-manager-entry-point",
        "ops-general-low-priority",
        "founding-pm-boundary",
    ]
    assert samples[0].snapshot.title == "Principal AI Engineer"
    assert samples[1].snapshot.v2_result["grade"] == "high"


def test_scoring_sample_suite_classifies_expected_v1_v2_differences():
    from app.services.scoring_samples import build_scoring_sample_suite

    samples = {sample.sample_id: sample for sample in build_scoring_sample_suite()}

    assert samples["principal-ai-no-pressure"].difference_kind == "v1_high_to_v2_medium"
    assert samples["urgent-backend-anomaly"].difference_kind == "v1_medium_to_v2_high"
    assert samples["bd-manager-entry-point"].difference_kind == "aligned"
    assert samples["ops-general-low-priority"].difference_kind == "aligned"


def test_scoring_sample_suite_exposes_reasons_that_support_manual_review():
    from app.services.scoring_samples import build_scoring_sample_suite, format_sample_summaries

    samples = build_scoring_sample_suite()
    summary_lines = format_sample_summaries(samples)

    assert any("Principal AI Engineer" in line and "high -> medium" in line for line in summary_lines)
    assert any("Backend Engineer" in line and "medium -> high" in line for line in summary_lines)
    assert any("招聘异常" in line or "时间压力" in line for line in summary_lines)


def test_scoring_sample_suite_results_stay_stable_for_boundary_case():
    from app.services.scoring_samples import build_scoring_sample_suite

    samples = {sample.sample_id: sample for sample in build_scoring_sample_suite()}
    boundary = samples["founding-pm-boundary"]

    assert boundary.snapshot.v1_result["grade"] == "high"
    assert boundary.snapshot.v2_result["grade"] == "high"
    assert boundary.snapshot.summary["grade_changed"] is False
