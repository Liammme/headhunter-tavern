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
        '{"key":"clue_1","title":"线索一：露出的口子","content":"这家公司值得优先关注。"},'
        '{"key":"clue_2","title":"线索二：卡住的岗位","content":"岗位比较关键。"},'
        '{"key":"clue_3","title":"线索三：下手路径","content":"建议持续观察。"}'
        ']}'
    )

    with pytest.raises(IntelligenceGenerationError, match="generic"):
        validate_company_clue_response(payload, context=build_context())


def test_validate_company_clue_response_requires_title_and_entry_point_grounding():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现，说明它在补关键推进位。",'
        '"sections":['
        '{"key":"clue_1","title":"线索一：露出的口子","content":"Principal AI Engineer 和 Growth Engineer 同时挂出，说明不是普通补人。"},'
        '{"key":"clue_2","title":"线索二：卡住的岗位","content":"Principal AI Engineer 代表核心技术推进，Growth Engineer 代表业务扩张。"},'
        '{"key":"clue_3","title":"线索三：下手路径","content":"先回到 https://jobs.example.com/1 核对团队职责，再看 https://jobs.example.com/2 是否仍在持续开放。"}'
        ']}'
    )

    validate_company_clue_response(payload, context=build_context())


def test_validate_company_clue_response_rejects_unapproved_next_move_entry_point():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现，说明它在补关键推进位。",'
        '"sections":['
        '{"key":"clue_1","title":"线索一：露出的口子","content":"Principal AI Engineer 和 Growth Engineer 同时挂出。"},'
        '{"key":"clue_2","title":"线索二：卡住的岗位","content":"Principal AI Engineer 和 Growth Engineer 都是可验证岗位。"},'
        '{"key":"clue_3","title":"线索三：下手路径","content":"先回到 https://jobs.example.com/1 核对职责，再联系 talent@fake.example。"}'
        ']}'
    )

    with pytest.raises(IntelligenceGenerationError, match="unapproved"):
        validate_company_clue_response(payload, context=build_context())


def test_parse_company_clue_response_rejects_invalid_json_as_generation_error():
    with pytest.raises(IntelligenceGenerationError, match="not valid JSON"):
        parse_company_clue_response("not json")


def test_parse_company_clue_response_builds_narrative_from_complete_sections():
    payload = parse_company_clue_response(
        '{"sections":{'
        '"clue_1":"Principal AI Engineer 和 Growth Engineer 同时挂出，像是某条能力线露出口子。",'
        '"clue_2":"Principal AI Engineer 暴露核心技术推进需求，Growth Engineer 暴露业务扩张需求。",'
        '"clue_3":"先查 https://jobs.example.com/1，再查 https://jobs.example.com/2。"'
        '}}'
    )

    assert payload["narrative"] == "Principal AI Engineer 和 Growth Engineer 同时挂出，像是某条能力线露出口子。"
    assert [section["key"] for section in payload["sections"]] == ["clue_1", "clue_2", "clue_3"]


def test_parse_company_clue_response_requires_section_title_and_content():
    with pytest.raises(IntelligenceGenerationError, match="missing title"):
        parse_company_clue_response(
            '{"narrative":"OpenGradient 有两个可验证岗位。",'
            '"sections":['
            '{"key":"clue_1","title":"","content":"Principal AI Engineer 正在开放。"},'
            '{"key":"clue_2","title":"线索二：卡住的岗位","content":"Principal AI Engineer。"},'
            '{"key":"clue_3","title":"线索三：下手路径","content":"先查 https://jobs.example.com/1。"}'
            ']}'
        )


def test_parse_company_clue_response_normalizes_section_object_shape():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"clue_1":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"clue_2":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"clue_3":"先查 https://jobs.example.com/1。"'
        '}}'
    )

    assert [section["key"] for section in payload["sections"]] == ["clue_1", "clue_2", "clue_3"]
    assert payload["sections"][0]["title"] == "线索一：露出的口子"
    assert payload["sections"][0]["content"] == "SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。"


def test_parse_company_clue_response_normalizes_chinese_section_object_keys():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"线索一：露出的口子":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"线索二：卡住的岗位":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"线索三：下手路径":"先查 https://jobs.example.com/1。"'
        '}}'
    )

    assert [section["key"] for section in payload["sections"]] == ["clue_1", "clue_2", "clue_3"]
    assert payload["sections"][2]["content"] == "先查 https://jobs.example.com/1。"


def test_parse_company_clue_response_normalizes_single_key_section_list_items():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 Backend Engineer 和 Lead Analytics Manager 同时暴露需求。",'
        '"sections":['
        '{"clue_1":"线索一：露出的口子\\nBackend Engineer 和 Lead Analytics Manager 同时挂出。"},'
        '{"clue_2":"线索二：卡住的岗位\\nBackend Engineer 指向 AML 框架，Lead Analytics Manager 指向分析管理。"},'
        '{"clue_3":"线索三：下手路径\\n先查 https://jobs.example.com/1，再查 https://jobs.example.com/2。"}'
        ']}'
    )

    assert [section["key"] for section in payload["sections"]] == ["clue_1", "clue_2", "clue_3"]
    assert payload["sections"][0]["title"] == "线索一：露出的口子"
    assert payload["sections"][0]["content"] == "Backend Engineer 和 Lead Analytics Manager 同时挂出。"


def test_parse_company_clue_response_inferrs_section_key_from_title():
    payload = parse_company_clue_response(
        '{"narrative":"BOT Chain 的 Project Manager 和 Partner Operation 同时暴露需求。",'
        '"sections":['
        '{"title":"线索一：露出的口子","content":"Project Manager 和 Partner Operation 同时出现。"},'
        '{"title":"线索二：卡住的岗位","content":"Project Manager 指向项目推进，Partner Operation 指向合作运营。"},'
        '{"title":"线索三：下手路径","content":"先查 https://jobs.example.com/1，再查 https://www.botchain.ai/。"}'
        ']}'
    )

    assert [section["key"] for section in payload["sections"]] == ["clue_1", "clue_2", "clue_3"]
    assert payload["sections"][2]["title"] == "线索三：下手路径"


def test_parse_company_clue_response_rejects_incomplete_section_object_shape():
    with pytest.raises(IntelligenceGenerationError, match="three sections"):
        parse_company_clue_response(
            '{"narrative":"Aijobs 的岗位还在窗口内。",'
            '"sections":{'
            '"clue_1":"SOL-1634 Senior Data Engineer 还在窗口内。",'
            '"clue_2":"SOL-1634 Senior Data Engineer 指向数据工程。"}'
            '}'
        )


def test_parse_company_clue_response_joins_section_object_list_content():
    payload = parse_company_clue_response(
        '{"narrative":"Aijobs 的 SOL-1634 Senior Data Engineer 和 AI Engineer 都在窗口内。",'
        '"sections":{'
        '"clue_1":"SOL-1634 Senior Data Engineer 和 AI Engineer 同时出现。",'
        '"clue_2":"SOL-1634 Senior Data Engineer 指向数据工程，AI Engineer 指向算法需求。",'
        '"clue_3":["先查 https://jobs.example.com/1。","再查 https://jobs.example.com/2。"]'
        '}}'
    )

    assert payload["sections"][2]["key"] == "clue_3"
    assert payload["sections"][2]["content"] == "先查 https://jobs.example.com/1。\n再查 https://jobs.example.com/2。"


def test_validate_company_clue_response_allows_markdown_link_for_approved_entry_point():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现。",'
        '"sections":['
        '{"key":"clue_1","title":"线索一：露出的口子","content":"Principal AI Engineer 和 Growth Engineer 同时挂出。"},'
        '{"key":"clue_2","title":"线索二：卡住的岗位","content":"Principal AI Engineer 和 Growth Engineer 都是可验证岗位。"},'
        '{"key":"clue_3","title":"线索三：下手路径","content":"先打开 [https://jobs.example.com/1](https://jobs.example.com/1) 核对职责。"}'
        ']}'
    )

    validate_company_clue_response(payload, context=build_context())
