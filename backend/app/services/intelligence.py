import json
from collections import Counter
from urllib import error, request

from app.core.config import settings
from app.services.feed_snapshot import DayBucketSnapshot, FeedMetadata


class IntelligenceGenerationError(RuntimeError):
    pass


def build_intelligence_snapshot(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata) -> dict:
    fallback_snapshot = build_rule_intelligence_snapshot(day_payloads, meta)
    if not _should_use_llm():
        return fallback_snapshot

    try:
        llm_fields = generate_llm_intelligence_fields(day_payloads, meta)
    except Exception:
        return fallback_snapshot

    return {
        **fallback_snapshot,
        "headline": llm_fields["headline"],
        "summary": llm_fields["summary"],
        "findings": llm_fields["findings"],
        "actions": llm_fields["actions"],
    }


def build_rule_intelligence_snapshot(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata) -> dict:
    companies = [company for day in day_payloads for company in day.companies]
    jobs = [job for company in companies for job in company.jobs]
    if not jobs:
        return {
            "headline": "近 14 天岗位池暂无新增信号，建议先触发抓取更新。",
            "summary": "当前情报基于统一聚合结果生成，但窗口内还没有可展示的公司与岗位。",
            "analysis_version": meta.analysis_version,
            "rule_version": meta.rule_version,
            "window_start": meta.window_start,
            "window_end": meta.window_end,
            "generated_at": meta.generated_at,
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
        for tag in job.tags
        if tag not in {"Senior", "核心岗位", "关键扩张", "长期挂岗", "高 BD 切入口"}
    )
    leading_tag = tag_counter.most_common(1)[0][0] if tag_counter else "核心"
    focus_companies = [company for company in companies if company.company_grade == "focus"]
    high_bounty_jobs = [job for job in jobs if job.bounty_grade == "high"]
    claimed_jobs = [job for job in jobs if job.claimed_names]

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
        "analysis_version": meta.analysis_version,
        "rule_version": meta.rule_version,
        "window_start": meta.window_start,
        "window_end": meta.window_end,
        "generated_at": meta.generated_at,
        "findings": findings,
        "actions": [
            "先看重点公司，再优先认领其中的高赏金岗位。",
            f"围绕 {leading_tag} 主线继续筛出未认领的核心岗位。",
            "对已认领岗位继续补充公司和团队判断，避免只盯单个职位。",
        ],
    }


def generate_llm_intelligence_fields(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata) -> dict:
    llm_input = build_llm_intelligence_input(day_payloads, meta)
    response_content = request_zhipu_chat_completion(llm_input)
    return parse_llm_intelligence_fields(response_content)


def build_llm_intelligence_input(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata) -> dict:
    companies = [company for day in day_payloads for company in day.companies]
    jobs = [job for company in companies for job in company.jobs]
    tag_counts = Counter(
        tag
        for job in jobs
        for tag in job.tags
        if tag not in {"Senior", "核心岗位", "关键扩张", "长期挂岗", "高 BD 切入口"}
    )
    bucket_stats = [
        {
            "bucket": day.bucket,
            "company_count": len(day.companies),
            "job_count": sum(len(company.jobs) for company in day.companies),
        }
        for day in day_payloads
    ]
    focus_companies = [
        {
            "company": company.company,
            "company_grade": company.company_grade,
            "job_count": company.total_jobs,
            "claimed_names": company.claimed_names,
        }
        for company in companies
        if company.company_grade == "focus"
    ][:5]
    representative_jobs = [
        {
            "company": company.company,
            "title": job.title,
            "bounty_grade": job.bounty_grade,
            "tags": job.tags,
            "claimed_names": job.claimed_names,
        }
        for company in companies
        for job in company.jobs
        if job.bounty_grade == "high"
    ][:8]

    return {
        "window": {
            "analysis_version": meta.analysis_version,
            "rule_version": meta.rule_version,
            "window_start": meta.window_start,
            "window_end": meta.window_end,
            "generated_at": meta.generated_at,
        },
        "overview": {
            "company_count": len(companies),
            "job_count": len(jobs),
            "high_bounty_job_count": sum(1 for job in jobs if job.bounty_grade == "high"),
            "claimed_job_count": sum(1 for job in jobs if job.claimed_names),
            "focus_company_count": sum(1 for company in companies if company.company_grade == "focus"),
        },
        "bucket_stats": bucket_stats,
        "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counts.most_common(8)],
        "focus_companies": focus_companies,
        "representative_jobs": representative_jobs,
    }


def request_zhipu_chat_completion(llm_input: dict) -> str:
    payload = {
        "model": settings.bounty_pool_zhipu_model,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是猎头团队的晨报分析助手。"
                    "你只能基于用户提供的聚合统计做判断，不能臆造未提供的数据。"
                    "请输出 JSON 对象，包含 headline、summary、findings、actions 四个字段。"
                    "headline 和 summary 必须是字符串。"
                    "findings 和 actions 必须是长度为 3 的字符串数组。"
                    "语言使用简洁、有判断力的中文，适合给猎头团队和老板同时阅读。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(llm_input, ensure_ascii=False),
            },
        ],
    }
    endpoint = f"{settings.bounty_pool_zhipu_base_url.rstrip('/')}/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.bounty_pool_zhipu_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=20) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IntelligenceGenerationError("LLM request failed") from exc

    try:
        message_content = response_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise IntelligenceGenerationError("LLM response is missing content") from exc

    if not isinstance(message_content, str):
        raise IntelligenceGenerationError("LLM response content must be a string")

    return message_content


def parse_llm_intelligence_fields(content: str) -> dict:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise IntelligenceGenerationError("LLM response is not valid JSON") from exc

    headline = payload.get("headline")
    summary = payload.get("summary")
    findings = payload.get("findings")
    actions = payload.get("actions")

    if not isinstance(headline, str) or not headline.strip():
        raise IntelligenceGenerationError("LLM response is missing headline")
    if not isinstance(summary, str) or not summary.strip():
        raise IntelligenceGenerationError("LLM response is missing summary")
    if not _is_string_list(findings):
        raise IntelligenceGenerationError("LLM response findings must be a string list")
    if not _is_string_list(actions):
        raise IntelligenceGenerationError("LLM response actions must be a string list")

    return {
        "headline": headline.strip(),
        "summary": summary.strip(),
        "findings": [item.strip() for item in findings[:3]],
        "actions": [item.strip() for item in actions[:3]],
    }


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and len(value) >= 1 and all(isinstance(item, str) and item.strip() for item in value)


def _should_use_llm() -> bool:
    return settings.bounty_pool_intelligence_llm_enabled and bool(settings.bounty_pool_zhipu_api_key)
