from collections import Counter


def build_intelligence_snapshot(day_payloads: list[dict]) -> dict:
    companies = [company for day in day_payloads for company in day["companies"]]
    jobs = [job for company in companies for job in company["jobs"]]
    if not jobs:
        return {
            "headline": "近 14 天岗位池暂无新增信号，建议先触发抓取更新。",
            "summary": "当前情报基于统一聚合结果生成，但窗口内还没有可展示的公司与岗位。",
            "findings": [
                "首页和情报当前共享同一聚合基线，因此这里为空时首页列表也应为空。",
            ],
            "actions": [
                "先触发抓取，等统一聚合结果生成后再判断主线方向。",
            ],
        }

    tag_counter = Counter(
        tag
        for job in jobs
        for tag in job["tags"]
        if tag not in {"Senior", "核心岗位", "关键扩张", "长期挂岗", "高 BD 切入口"}
    )
    leading_tag = tag_counter.most_common(1)[0][0] if tag_counter else "核心"
    focus_companies = [company for company in companies if company["company_grade"] == "focus"]
    high_bounty_jobs = [job for job in jobs if job["bounty_grade"] == "high"]
    claimed_jobs = [job for job in jobs if job["claimed_names"]]

    findings = [
        f"重点公司 {len(focus_companies)} 家，优先顺着公司卡往下打。",
        f"已认领 {len(claimed_jobs)} 个岗位，继续优先补齐未认领高赏金岗位。",
    ]
    if leading_tag == "AI":
        findings.insert(0, "AI 相关岗位仍是当前窗口内最强主线。")
    else:
        findings.insert(0, f"{leading_tag} 相关岗位在当前窗口内出现频率最高。")

    return {
        "headline": f"近 14 天 {leading_tag} 岗位活跃，建议优先跟进高赏金与重点公司。",
        "summary": (
            f"基于近 14 天统一聚合结果生成：{len(companies)} 家公司，"
            f"{len(jobs)} 个岗位，{len(high_bounty_jobs)} 个高赏金岗位。"
        ),
        "findings": findings,
        "actions": [
            "先看重点公司，再优先认领其中的高赏金岗位。",
            f"围绕 {leading_tag} 主线继续筛出未认领的核心岗位。",
            "对已认领岗位继续补充公司和团队判断，避免只盯单个职位。",
        ],
    }
