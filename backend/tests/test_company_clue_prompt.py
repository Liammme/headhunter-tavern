from app.services.company_clue_prompt import build_company_clue_rewrite_messages, build_company_clue_system_prompt


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
    assert "clue_3" in rewrite_prompt


def test_system_prompt_uses_detective_clue_sections():
    prompt = build_company_clue_system_prompt()

    assert "猎头酒馆里的线索侦探" in prompt
    assert "clue_1" in prompt
    assert "clue_2" in prompt
    assert "clue_3" in prompt
    assert "线索一：需求信号" in prompt
    assert "线索二：关键岗位" in prompt
    assert "线索三：行动入口" in prompt
