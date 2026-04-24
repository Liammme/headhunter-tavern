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


def test_parse_company_clue_response_normalizes_section_object_shape():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"lead":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"evidence":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"next_move":"先查 https://jobs.example.com/1。"'
        '}}'
    )

    assert [section["key"] for section in payload["sections"]] == ["lead", "evidence", "next_move"]
    assert payload["sections"][0]["title"] == "为什么现在值得查"
    assert payload["sections"][0]["content"] == "SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。"


def test_parse_company_clue_response_normalizes_chinese_section_object_keys():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"为什么现在值得查":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"最能代表需求的岗位":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"你下一步先验证什么":"先查 https://jobs.example.com/1。"'
        '}}'
    )

    assert [section["key"] for section in payload["sections"]] == ["lead", "evidence", "next_move"]
    assert payload["sections"][2]["content"] == "先查 https://jobs.example.com/1。"


def test_parse_company_clue_response_rejects_incomplete_section_object_shape():
    with pytest.raises(IntelligenceGenerationError, match="three sections"):
        parse_company_clue_response(
            '{"narrative":"Aijobs 的岗位还在窗口内。",'
            '"sections":{'
            '"lead":"SOL-1634 Senior Data Engineer 还在窗口内。",'
            '"evidence":"SOL-1634 Senior Data Engineer 指向数据工程。"}'
            '}'
        )


def test_parse_company_clue_response_joins_section_object_list_content():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"lead":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"evidence":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"next_move":["先查 https://jobs.example.com/1。","再查 https://jobs.example.com/2。"]'
        '}}'
    )

    assert payload["sections"][2]["key"] == "next_move"
    assert payload["sections"][2]["content"] == "先查 https://jobs.example.com/1。\n再查 https://jobs.example.com/2。"


def test_validate_company_clue_response_allows_markdown_link_for_approved_entry_point():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 和 Growth Engineer 同时挂出。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 和 Growth Engineer 都是可验证岗位。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"先打开 [https://jobs.example.com/1](https://jobs.example.com/1) 核对职责。"}'
        ']}'
    )

    validate_company_clue_response(payload, context=build_context())
