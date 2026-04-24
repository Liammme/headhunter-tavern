import pytest

from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import IntelligenceGenerationError


def build_context() -> dict:
    return {
        "company": "OpenGradient",
        "summary": {"total_jobs": 2},
        "evidence_cards": [
            {
                "title": "Principal AI Engineer",
                "entry_points": {
                    "job_post": "https://jobs.example.com/1",
                    "company_url": None,
                    "hiring_page": None,
                    "email": None,
                },
            },
            {
                "title": "Growth Engineer",
                "entry_points": {
                    "job_post": "https://jobs.example.com/2",
                    "company_url": None,
                    "hiring_page": None,
                    "email": None,
                },
            },
        ],
        "entry_points": {
            "job_posts": ["https://jobs.example.com/1", "https://jobs.example.com/2"],
            "company_urls": [],
            "hiring_pages": [],
            "emails": [],
        },
    }


def test_validate_company_clue_response_rejects_generic_copy():
    payload = parse_company_clue_response(
        '{"narrative":"OpenGradient 表现突出，整体热度高，值得优先关注。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"这家公司值得优先关注。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"岗位比较关键。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"建议持续观察。"}'
        ']}'
    )

    with pytest.raises(IntelligenceGenerationError, match="generic"):
        validate_company_clue_response(payload, context=build_context())


def test_validate_company_clue_response_requires_title_and_entry_point_grounding():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现，说明它在补关键推进位。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 和 Growth Engineer 同时挂出，说明不是普通补人。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 代表核心技术推进，Growth Engineer 代表业务扩张。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"先回到 https://jobs.example.com/1 核对团队职责，再看 https://jobs.example.com/2 是否仍在持续开放。"}'
        ']}'
    )

    validate_company_clue_response(payload, context=build_context())


def test_validate_company_clue_response_rejects_unapproved_next_move_entry_point():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现，说明它在补关键推进位。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 和 Growth Engineer 同时挂出。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 和 Growth Engineer 都是可验证岗位。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"先回到 https://jobs.example.com/1 核对职责，再联系 talent@fake.example。"}'
        ']}'
    )

    with pytest.raises(IntelligenceGenerationError, match="unapproved"):
        validate_company_clue_response(payload, context=build_context())


def test_parse_company_clue_response_rejects_invalid_json_as_generation_error():
    with pytest.raises(IntelligenceGenerationError, match="not valid JSON"):
        parse_company_clue_response("not json")


def test_parse_company_clue_response_requires_section_title_and_content():
    with pytest.raises(IntelligenceGenerationError, match="missing title"):
        parse_company_clue_response(
            '{"narrative":"OpenGradient 有两个可验证岗位。",'
            '"sections":['
            '{"key":"lead","title":"","content":"Principal AI Engineer 正在开放。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先查 https://jobs.example.com/1。"}'
            ']}'
        )
