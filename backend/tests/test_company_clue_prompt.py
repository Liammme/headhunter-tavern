from app.services.company_clue_prompt import build_company_clue_rewrite_messages


def test_rewrite_prompt_does_not_require_two_titles_for_single_evidence_card():
    messages = build_company_clue_rewrite_messages(
        context={
            "company": "OpenGradient",
            "evidence_cards": [{"title": "Principal AI Engineer"}],
            "entry_points": {"job_posts": ["https://jobs.example.com/1"]},
        },
        invalid_content="{}",
        validation_error="generic",
    )

    rewrite_prompt = messages[1]["content"]

    assert "至少 2 个岗位标题" not in rewrite_prompt
    assert "evidence_cards 里的岗位标题" in rewrite_prompt
