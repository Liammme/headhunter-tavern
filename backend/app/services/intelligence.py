import json
import logging
from collections import Counter
from app.models import Job
from app.services.feed_snapshot import DayBucketSnapshot, FeedMetadata
from app.services.job_facts import StandardizedJobInput, build_v2_score_input, extract_job_facts
from app.services.llm_client import (
    LlmClientError,
    iter_llm_models,
    request_chat_completion_with_model,
    should_use_llm,
)
from app.services.scoring import score_job_v2


class IntelligenceGenerationError(RuntimeError):
    pass


logger = logging.getLogger(__name__)
REPORT_TONE_PHRASES = (
    "根据数据分析可得",
    "本周市场动态显示",
    "综合来看",
    "分析报告",
    "市场动态",
    "周报",
)
GENERIC_ACTION_PHRASES = (
    "制定专项方案",
    "加强关注",
    "主动接触候选人",
    "联系已报备的人",
    "利用已报备线索",
)


def build_intelligence_snapshot(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata, jobs: list[Job] | None = None) -> dict:
    fallback_snapshot = build_rule_intelligence_snapshot(day_payloads, meta)
    if not _should_use_llm():
        return fallback_snapshot

    try:
        llm_fields = generate_llm_intelligence_fields(day_payloads, meta, jobs=jobs or [])
    except Exception as exc:
        logger.warning("Falling back to rule-based intelligence summary: %s", exc)
        return fallback_snapshot

    return {
        **fallback_snapshot,
        "narrative": llm_fields["narrative"],
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
            "narrative": "近 14 天岗位池暂无新增信号，建议先触发抓取更新。当前情报基于统一聚合结果生成，但窗口内还没有可展示的公司与岗位。你抬眼示意他继续，吧台另一头只回了一句：首页和情报当前共享同一聚合基线，因此这里为空时首页列表也应为空。最后只剩一句落在桌面上：先触发抓取，等统一聚合结果生成后再判断主线方向。",
            "headline": "James侦探把杯子往吧台边一推：近 14 天岗位池暂时没起风，先把抓取拉起来再看下一步。",
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

    snapshot = {
        "headline": f"James侦探晃了晃杯底，低声说：今天先盯那些把{leading_tag}核心岗位重新往前顶的公司。",
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
    snapshot["narrative"] = build_narrative_from_fields(
        headline=snapshot["headline"],
        summary=snapshot["summary"],
        findings=snapshot["findings"],
        actions=snapshot["actions"],
    )
    return snapshot


def generate_llm_intelligence_fields(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata, jobs: list[Job]) -> dict:
    llm_input = build_llm_intelligence_input(day_payloads, meta, jobs=jobs)
    response_content = request_zhipu_chat_completion(llm_input)
    banned_names = collect_claimed_names(day_payloads)
    try:
        parsed = parse_llm_intelligence_fields(response_content)
        validate_llm_intelligence_fields(parsed, banned_names=banned_names)
        return parsed
    except IntelligenceGenerationError as exc:
        repaired_content = rewrite_llm_intelligence_fields(
            llm_input=llm_input,
            invalid_content=response_content,
            validation_error=str(exc),
        )
        repaired = parse_llm_intelligence_fields(repaired_content)
        validate_llm_intelligence_fields(repaired, banned_names=banned_names)
        return repaired


def build_llm_intelligence_input(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata, jobs: list[Job]) -> dict:
    companies = [company for day in day_payloads for company in day.companies]
    feed_jobs = [job for company in companies for job in company.jobs]
    tag_counts = Counter(
        tag
        for job in feed_jobs
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
            "job_count": len(feed_jobs),
            "high_bounty_job_count": sum(1 for job in feed_jobs if job.bounty_grade == "high"),
            "claimed_job_count": sum(1 for job in feed_jobs if job.claimed_names),
            "focus_company_count": sum(1 for company in companies if company.company_grade == "focus"),
        },
        "bucket_stats": bucket_stats,
        "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counts.most_common(8)],
        "focus_companies": focus_companies,
        "representative_jobs": representative_jobs,
        "job_fact_briefs": build_job_fact_briefs(jobs_by_id={job.id: job for job in jobs}, day_payloads=day_payloads),
    }


def request_zhipu_chat_completion(llm_input: dict) -> str:
    messages = [
        {
            "role": "system",
            "content": build_intelligence_system_prompt(),
        },
        {
            "role": "user",
            "content": build_intelligence_user_prompt(llm_input),
        },
    ]
    return _request_zhipu_chat_completion_with_retry(messages)


def request_zhipu_structured_json(messages: list[dict]) -> str:
    return _request_zhipu_chat_completion_with_retry(messages)


def rewrite_llm_intelligence_fields(*, llm_input: dict, invalid_content: str, validation_error: str) -> str:
    messages = [
        {
            "role": "system",
            "content": build_intelligence_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "你上一版输出不合格，请只修正为合格 JSON，不要解释。"
                f"不合格原因：{validation_error}。"
                "你必须保留 James侦探 角色、酒馆情报口吻、直接清楚的判断。"
                "你必须给出 narrative 完整短报，前端会直接显示这段 narrative。"
                "你必须去掉报告腔、统计播报、联系人/候选人动作。"
                "findings 和 actions 各只写 1 条。"
                f"\n\n原始结构化输入：\n{json.dumps(llm_input, ensure_ascii=False)}"
                f"\n\n你上一版输出：\n{invalid_content}"
            ),
        },
    ]
    return _request_zhipu_chat_completion_with_retry(messages)


def _request_zhipu_chat_completion_with_retry(messages: list[dict]) -> str:
    errors: list[str] = []
    for model_name in _iter_zhipu_models():
        try:
            return _request_zhipu_chat_completion_with_model(messages, model_name)
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")

    raise IntelligenceGenerationError("; ".join(errors))


def _request_zhipu_chat_completion_with_model(messages: list[dict], model_name: str) -> str:
    try:
        return request_chat_completion_with_model(messages, model_name)
    except LlmClientError as exc:
        raise IntelligenceGenerationError(str(exc)) from exc

def build_intelligence_system_prompt() -> str:
    return (
        "你是 James侦探，常在猎头酒馆里低声递情报，但表达必须直接、清楚，不装神秘。"
        "你只能基于用户提供的结构化输入判断，不能臆造未提供的数据，也不能引用输入里不存在的公司、岗位、人物。"
        "请直接输出 JSON 对象，不要输出额外解释，不要输出 markdown。"
        "JSON 必须包含 narrative、headline、summary、findings、actions 五个字段。"
        "narrative、headline 和 summary 必须是字符串。findings 和 actions 必须是字符串数组，且各只写 1 条。"
        "narrative 是前端直接显示的主文案，必须是一段 250 到 400 字的情报短报，不是列表，不是报告。"
        "固定结构必须是：James侦探出场一句；他说今天相对近14天哪里变了；你追问一句或示意他继续，他解释判断；最后留一句今天该先盯什么公司类型和岗位类型。"
        "第三段必须显式出现追问环节，至少包含“你示意他继续”或“你抬眼示意他继续”这类表达，不能省略。"
        "角色感占三成，判断和信息占七成。可以有一点酒馆里交换情报的气味，但不能写成谜语、小说或周报。"
        "重点必须回答：今天和近14天基线相比，猎场哪里变了；这个变化说明什么；今天更该先盯什么公司类型和岗位类型。"
        "禁止纯统计播报，不能只重复标签次数、公司数量、岗位数量。"
        "禁止报告腔，例如“根据数据分析可得”“本周市场动态显示”“综合来看”。"
        "禁止空泛建议，例如“制定专项方案”“加强关注”“主动接触候选人”。"
        "认领人只表示内部占坑状态，不是联系人，不是候选人，不是行动线索。"
        "禁止引用任何认领人名字，禁止写“联系已报备的人”“利用已报备线索”。"
        "请严格模仿下面这个 JSON 风格，只替换成当前输入对应的内容："
        '{"narrative":"James侦探晃了晃杯底，低声说：今天先盯那些把核心产研岗重新往前顶的公司。他说，和近14天摊开的盘子比，今天真正冒头的不是热闹标签，而是更集中地压在高赏金、业务关键、时间压力更高的岗位上。你示意他继续，他把话说透：这说明市场不是单纯变热，而是企业更愿意把真正卡节奏的岗位先往外放，尤其是技术、AI和产品里带负责人味道的岗位。他把杯子推回来，只留一句：今天更该先盯重点公司和持续招不动的团队，优先抢技术、AI、产品里的高赏金核心岗。",'
        '"headline":"James侦探晃了晃杯底，低声说：今天先盯那些把核心产研岗重新往前顶的公司。",'
        '"summary":"他说，和近14天摊开的盘子比，今天真正冒头的不是热闹标签，而是更集中地压在高赏金、业务关键、时间压力更高的岗位上。",'
        '"findings":["你示意他继续，他把话说透：这说明市场不是单纯变热，而是企业更愿意把真正卡节奏的岗位先往外放，尤其是技术、AI和产品里带负责人味道的岗位。"],'
        '"actions":["他把杯子推回来，只留一句：今天更该先盯重点公司和持续招不动的团队，优先抢技术、AI、产品里的高赏金核心岗。"]}'
    )


def build_intelligence_user_prompt(llm_input: dict) -> str:
    return (
        "请基于下面的统一分析基线生成猎场情报。"
        "优先使用 job_fact_briefs 解释今天相对近14天的变化，点名 1 到 3 个真正代表变化的公司或岗位方向即可。"
        "不要做标签播报，不要写管理建议，不要写联系人动作。"
        "输出时先写好 narrative 这段完整短报，前端会直接显示 narrative 原文。"
        "headline、summary、findings、actions 只是兼容字段，内容必须与 narrative 对齐。"
        "第三段必须写出你追问或示意他继续，再由他把判断说透。"
        "headline 必须以 James侦探 开头。findings 和 actions 各只写 1 条完整句子。"
        f"\n\n结构化输入：\n{json.dumps(llm_input, ensure_ascii=False)}"
    )


def parse_llm_intelligence_fields(content: str) -> dict:
    normalized_content = _strip_code_fence(content)
    try:
        payload = json.loads(normalized_content)
    except json.JSONDecodeError as exc:
        raise IntelligenceGenerationError("LLM response is not valid JSON") from exc

    headline = payload.get("headline")
    narrative = payload.get("narrative")
    summary = payload.get("summary")
    findings = payload.get("findings")
    actions = payload.get("actions")

    if not isinstance(narrative, str) or not narrative.strip():
        raise IntelligenceGenerationError("LLM response is missing narrative")
    if not isinstance(headline, str) or not headline.strip():
        raise IntelligenceGenerationError("LLM response is missing headline")
    if not isinstance(summary, str) or not summary.strip():
        raise IntelligenceGenerationError("LLM response is missing summary")
    if not _is_string_list(findings):
        raise IntelligenceGenerationError("LLM response findings must be a string list")
    if not _is_string_list(actions):
        raise IntelligenceGenerationError("LLM response actions must be a string list")

    return {
        "narrative": narrative.strip(),
        "headline": headline.strip(),
        "summary": summary.strip(),
        "findings": [item.strip() for item in findings[:3]],
        "actions": [item.strip() for item in actions[:3]],
    }


def validate_llm_intelligence_fields(payload: dict, *, banned_names: set[str]) -> None:
    text_parts = [payload["narrative"], payload["headline"], payload["summary"], *payload["findings"], *payload["actions"]]
    joined = " ".join(text_parts)
    narrative = payload["narrative"]

    if "James侦探" not in payload["headline"]:
        raise IntelligenceGenerationError("LLM response is missing James侦探 framing")
    if "James侦探" not in narrative:
        raise IntelligenceGenerationError("LLM response narrative is missing James侦探 framing")

    for name in banned_names:
        if name and name in joined:
            raise IntelligenceGenerationError("LLM response leaked claimed_names")

    for phrase in REPORT_TONE_PHRASES + GENERIC_ACTION_PHRASES:
        if phrase in joined:
            raise IntelligenceGenerationError(f"LLM response used banned phrase: {phrase}")

    if "你示意他继续" not in narrative and "你抬眼示意他继续" not in narrative:
        raise IntelligenceGenerationError("LLM response is missing the follow-up beat")

    if "标签" in joined and ("出现" in joined or "达" in joined):
        raise IntelligenceGenerationError("LLM response fell back to tag count broadcast")


def build_narrative_from_fields(*, headline: str, summary: str, findings: list[str], actions: list[str]) -> str:
    clean_findings = [item.strip() for item in findings if item.strip()]
    clean_actions = [item.strip() for item in actions if item.strip()]
    follow_up = clean_findings[0] if clean_findings else ""
    if follow_up and "你示意他继续" not in follow_up and "你抬眼示意他继续" not in follow_up:
        follow_up = f"你抬眼示意他继续，{follow_up}"

    segments = [
        headline.strip(),
        follow_up,
        *clean_actions,
    ]
    return " ".join(segments)


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and len(value) >= 1 and all(isinstance(item, str) and item.strip() for item in value)


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped


def _should_use_llm() -> bool:
    return should_use_llm()


def _iter_zhipu_models() -> list[str]:
    return iter_llm_models()

def collect_claimed_names(day_payloads: list[DayBucketSnapshot]) -> set[str]:
    claimed_names: set[str] = set()
    for day in day_payloads:
        for company in day.companies:
            claimed_names.update(name for name in company.claimed_names if name)
            for job in company.jobs:
                claimed_names.update(name for name in job.claimed_names if name)
    return claimed_names


def build_job_fact_briefs(*, jobs_by_id: dict[int, Job], day_payloads: list[DayBucketSnapshot]) -> list[dict]:
    briefs: list[dict] = []
    for day in day_payloads:
        for company in day.companies:
            for feed_job in company.jobs:
                job = jobs_by_id.get(feed_job.id)
                if job is None:
                    continue

                facts = extract_job_facts(
                    StandardizedJobInput(
                        canonical_url=job.canonical_url,
                        source_name=job.source_name,
                        title=job.title,
                        company=job.company,
                        company_normalized=job.company_normalized,
                        description=job.description,
                        posted_at=job.posted_at,
                        collected_at=job.collected_at,
                    ),
                    now=job.collected_at,
                )
                score_result = score_job_v2(build_v2_score_input(facts))
                briefs.append(
                    {
                        "bucket": day.bucket,
                        "company": company.company,
                        "company_grade": company.company_grade,
                        "title": feed_job.title,
                        "bounty_grade": feed_job.bounty_grade,
                        "category": facts.category,
                        "domain_tag": facts.domain_tag,
                        "seniority": facts.seniority,
                        "urgent": facts.urgent,
                        "critical": facts.critical,
                        "bd_entry": facts.bd_entry,
                        "hard_to_fill": facts.hard_to_fill,
                        "role_complexity": facts.role_complexity,
                        "business_criticality": facts.business_criticality,
                        "anomaly_signals": list(facts.anomaly_signals),
                        "time_pressure_signals": list(facts.time_pressure_signals),
                        "display_tags": list(feed_job.tags),
                        "reasons": list(score_result.reasons),
                    }
                )

    briefs.sort(
        key=lambda item: (
            {"today": 0, "yesterday": 1, "earlier": 2}.get(item["bucket"], 3),
            {"focus": 0, "watch": 1, "normal": 2}.get(item["company_grade"], 3),
            {"high": 0, "medium": 1, "low": 2}.get(item["bounty_grade"], 3),
            item["company"].lower(),
            item["title"].lower(),
        )
    )
    return briefs[:12]
