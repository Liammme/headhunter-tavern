import json


def build_company_clue_messages(context: dict) -> list[dict]:
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {"role": "user", "content": build_company_clue_user_prompt(context)},
    ]


def build_company_clue_rewrite_messages(*, context: dict, invalid_content: str, validation_error: str) -> list[dict]:
    title_requirement = _build_title_requirement(context)
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {
            "role": "user",
            "content": (
                "你上一版输出不合格，请只修正为合格 JSON。"
                f"不合格原因：{validation_error}。"
                "必须保留现有响应 schema：narrative + sections。"
                f"{title_requirement}，必须把 clue_3 绑定到真实入口，禁止泛泛建议。"
                "sections 必须是数组，key 固定为 clue_1、clue_2、clue_3。"
                f"\n\n结构化输入：\n{json.dumps(context, ensure_ascii=False)}"
                f"\n\n上一版输出：\n{invalid_content}"
            ),
        },
    ]


def build_company_clue_system_prompt() -> str:
    return (
        "你是猎头酒馆里的线索侦探，正在写单公司线索案卷，不是商业分析师。"
        "只能依据用户给你的结构化输入判断，不能编造外部信息。"
        "直接输出 JSON 对象，不要 markdown。"
        "JSON 必须包含 narrative 和 sections。"
        "sections 必须是 3 个对象组成的数组。"
        "sections 的 key 必须固定为 clue_1、clue_2、clue_3。"
        "clue_1 标题固定为“线索一：需求信号”，写这家公司在 14 天岗位窗口里哪里不对劲。"
        "clue_2 标题固定为“线索二：关键岗位”，必须点名 evidence_cards 里的具体岗位标题，并说明每个岗位暴露的需求。"
        "clue_3 标题固定为“线索三：行动入口”，给出 2-3 个猎头摸排动作，每个动作必须绑定真实入口。"
        "必须优先引用 evidence_cards 里的岗位标题、信号、片段和入口。"
        "必须区分事实和推断，不要把推断写成事实。"
        "禁止使用“表现突出”“值得优先关注”“整体热度高”“建议持续观察”这类泛化表述。"
    )


def build_company_clue_user_prompt(context: dict) -> str:
    return (
        "请基于下面的公司证据包生成一份单公司线索案卷。"
        "你要像侦探拆案，不要像咨询报告。"
        "不要写“为什么值得关注”，要写“它哪里不对劲”。"
        "不要写泛泛建议，要写下一步从哪个真实入口摸排。"
        "如果 context 里有两个以上 evidence_cards，全文必须至少点名两个岗位标题。"
        "clue_1 写公司级异常：岗位集中方向、时间压力、岗位层级、长期挂岗或相邻岗位同时出现。"
        "clue_2 写关键岗位证据：点名 2-3 个真实岗位标题，并说明它们暴露了什么需求。"
        "clue_3 写猎头行动入口：2-3 个动作，每个动作必须绑定真实 job_post、hiring_page、company_url 或 email。"
        "如果没有公司官网或邮箱，就只允许引用 job_posts。"
        "sections 的标题固定写成“线索一：需求信号”“线索二：关键岗位”“线索三：行动入口”。"
        f"\n\n结构化输入：\n{json.dumps(context, ensure_ascii=False)}"
    )


def _build_title_requirement(context: dict) -> str:
    if len(context.get("evidence_cards", [])) >= 2:
        return "必须点名至少 2 个岗位标题"
    return "必须点名 evidence_cards 里的岗位标题"
