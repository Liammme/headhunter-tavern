from app.services.job_category_classifier import classify_job_category_result
from app.services.job_facts import classify_job_category


def test_classify_job_category_covers_filter_taxonomy():
    cases = [
        ("Senior UX Designer", "", "设计"),
        ("Community Operations Manager", "", "运营"),
        ("Growth Marketing Manager", "", "市场"),
        ("Account Executive", "", "销售"),
        ("Business Development Manager", "", "商务"),
        ("Product Manager", "", "产品"),
        ("Backend Engineer", "", "技术"),
        ("Machine Learning Engineer", "", "AI/算法"),
        ("Senior Data Engineer", "", "数据"),
        ("Security Engineer", "", "安全"),
        ("Developer Advocate", "", "DevRel/社区"),
        ("Talent Acquisition Partner", "", "财务/法务/HR"),
        ("Senior Scientist, Computational Chemist", "", "其他"),
    ]

    for title, description, expected in cases:
        assert classify_job_category(title, description) == expected


def test_title_match_beats_description_noise():
    result = classify_job_category_result(
        "Senior Data Engineer",
        "Work with platform, backend services, AI tooling, and customer delivery.",
    )

    assert result.primary == "数据"
    assert "技术" in result.secondary
    assert result.confidence == "medium"
    assert result.reason == "title keyword match"


def test_description_is_only_fallback_when_title_is_unclear():
    result = classify_job_category_result(
        "Specialist",
        "Own KYC, AML, fraud, and compliance operations.",
    )

    assert result.primary == "安全"
    assert result.confidence == "low"
    assert result.reason == "description keyword fallback"


def test_mixed_job_posting_is_not_forced_into_a_specific_filter_category():
    result = classify_job_category_result(
        "以下岗位投递 @hr\n产品经理\nUI Designer\nBackend Engineer\nBD Manager",
        "",
    )

    assert result.primary == "其他"
    assert result.secondary == ()
    assert result.confidence == "low"
    assert result.mixed_job_posting is True
