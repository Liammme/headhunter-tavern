from app.services.scoring import derive_company_grade, derive_job_grade


def test_job_grade_prefers_core_tech_roles():
    grade = derive_job_grade(
        title="Senior AI Engineer",
        category="AI/算法",
        signals={"urgent": True, "critical": True, "bd_entry": False},
    )

    assert grade == "high"


def test_company_grade_uses_majority_job_grade():
    grade = derive_company_grade(["high", "medium", "medium"])

    assert grade == "watch"


def test_company_grade_ignores_invalid_values_and_handles_tie_conservatively():
    grade = derive_company_grade(["high", "medium", "unknown"])

    assert grade == "watch"
