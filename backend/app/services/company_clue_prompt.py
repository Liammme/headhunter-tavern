import json


def build_company_clue_messages(context: dict) -> list[dict]:
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {"role": "user", "content": build_company_clue_user_prompt(context)},
    ]


def build_company_clue_rewrite_messages(*, context: dict, invalid_content: str, validation_error: str) -> list[dict]:
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {
            "role": "user",
            "content": (
                "你上一版输出不合格，请只修正为合格 JSON。"
                f"不合格原因：{validation_error}。"
                "必须保留现有响应 schema：narrative + sections。"
                "必须点名至少 2 个岗位标题，必须把 next_move 绑定到真实入口，禁止泛泛建议。"
                f"\n\n结构化输入：\n{json.dumps(context, ensure_ascii=False)}"
                f"\n\n上一版输出：\n{invalid_content}"
            ),
        },
    ]


def build_company_clue_system_prompt() -> str:
    return (
        "你是猎头酒馆里的 BD 侦查员，正在写单公司 BD 作战简报。"
        "只能依据用户给你的结构化输入判断，不能编造外部信息。"
        "直接输出 JSON 对象，不要 markdown。"
        "JSON 必须包含 narrative 和 sections。"
        "sections 必须固定为 lead、evidence、next_move 三段。"
        "lead 要回答为什么现在值得查；evidence 要点名最能代表需求的岗位；next_move 要给出 3 个可执行验证动作。"
        "必须优先引用 evidence_cards 里的岗位标题、信号、片段和入口。"
        "禁止使用“表现突出”“值得优先关注”“整体热度高”“建议持续观察”这类泛化表述。"
    )


def build_company_clue_user_prompt(context: dict) -> str:
    return (
        "请基于下面的公司证据包生成单公司 BD 作战简报。"
        "必须区分已知事实和推断，不要把推断写成事实。"
        "如果 context 里有两个以上 evidence_cards，全文必须至少点名两个岗位标题。"
        "next_move 必须绑定真实入口链接或邮箱；如果没有公司官网或邮箱，就只允许引用 job_posts。"
        "sections 的标题固定写成“为什么现在值得查”“最能代表需求的岗位”“你下一步先验证什么”。"
        f"\n\n结构化输入：\n{json.dumps(context, ensure_ascii=False)}"
    )
