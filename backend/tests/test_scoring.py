from app.services.scoring import JobScoreInput, score_job, derive_company_grade


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
