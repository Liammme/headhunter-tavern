import json
import logging
import time
from collections import Counter

from app.models import Job
from app.services.feed_snapshot import DayBucketSnapshot, FeedMetadata
from app.services.intelligence_context import build_intelligence_change_context
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
TRANSIENT_LLM_RETRY_DELAYS = (1, 2)
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
    fallback_snapshot = build_rule_intelligence_snapshot(day_payloads, meta, jobs=jobs)
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


def build_rule_intelligence_snapshot(day_payloads: list[DayBucketSnapshot], meta: FeedMetadata, jobs: list[Job] | None = None) -> dict:
    if jobs and _has_window_feed_jobs(day_payloads):
        change_context = build_intelligence_change_context(jobs=jobs, meta=meta)
        change_snapshot = _build_rule_intelligence_snapshot_from_change_context(change_context, meta)
        if change_snapshot is not None:
            return change_snapshot

    companies = [company for day in day_payloads for company in day.companies]
    jobs = [job for company in companies for job in company.jobs]
    if not jobs:
        return {
            "narrative": "近 14 天岗位池暂无新增信号，建议先触发抓取更新。当前情报基于统一聚合结果生成，但窗口内还没有可展示的公司与岗位。首页和情报当前共享同一聚合基线，因此这里为空时首页列表也应为空。下一步先触发抓取，等统一聚合结果生成后再判断主线方向。",
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

    snapshot = {
        "headline": f"今日重点：{leading_tag} 核心岗位仍是当前窗口内最明确的主线。",
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


def _has_window_feed_jobs(day_payloads: list[DayBucketSnapshot]) -> bool:
    return any(company.jobs for day in day_payloads for company in day.companies)


def _build_rule_intelligence_snapshot_from_change_context(change_context: dict, meta: FeedMetadata) -> dict | None:
    representative_changes = change_context["representative_changes"]
    first_change = representative_changes[0]
    if first_change["change_type"] == "no_today_change":
        headline = "今天暂无可验证的新升温信号，先不要把旧盘面解读成新变化。"
        summary = "今天没有可验证的新公司、新类目或新领域升温，情报降级为稳定提示。"
        findings = ["今天的岗位池没有给出足够证据证明盘面发生了新变化。"]
        actions = ["今天先复核既有重点公司和高赏金岗位，等新增信号出现后再切换主线。"]
    else:
        evidence = first_change["evidence"][0] if first_change["evidence"] else {}
        company = evidence.get("company", "当前公司")
        title = evidence.get("title", "核心岗位")
        category = evidence.get("category", "核心")
        domain = evidence.get("domain_tag", "重点领域")
        headline = f"今日重点：先看 {company} 带出来的 {domain} 变化。"
        summary = f"今天真正变化的是 {first_change['summary']} 代表岗位是 {company} 的 {title}。"
        findings = [
            f"这不是复述近14天总量，而是今天在 {category} / {domain} 上出现了可点名的新增或升温证据。"
        ]
        actions = [f"今天先盯 {company} 这类公司，以及 {category} 里的高赏金核心岗。"]

    return {
        "headline": headline,
        "summary": summary,
        "analysis_version": meta.analysis_version,
        "rule_version": meta.rule_version,
        "window_start": meta.window_start,
        "window_end": meta.window_end,
        "generated_at": meta.generated_at,
        "findings": findings,
        "actions": actions,
        "narrative": build_narrative_from_fields(
            headline=headline,
            summary=summary,
            findings=findings,
            actions=actions,
        ),
    }


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
        "change_context": build_intelligence_change_context(jobs=jobs, meta=meta),
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
                "你必须使用正常、直接、清楚的业务情报文案，不要使用角色扮演、人设口吻或故事化表达。"
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
    model_names = _iter_zhipu_models()
    total_attempts = 1 + len(TRANSIENT_LLM_RETRY_DELAYS)
    for attempt_index in range(total_attempts):
        attempt_errors: list[Exception] = []
        for model_name in model_names:
            try:
                return _request_zhipu_chat_completion_with_model(messages, model_name)
            except Exception as exc:
                errors.append(f"{model_name}: {exc}")
                attempt_errors.append(exc)
        has_retry_left = attempt_index < len(TRANSIENT_LLM_RETRY_DELAYS)
        if has_retry_left and attempt_errors and all(_is_transient_llm_error(exc) for exc in attempt_errors):
            time.sleep(TRANSIENT_LLM_RETRY_DELAYS[attempt_index])
            continue
        if not has_retry_left:
            break

    raise IntelligenceGenerationError("; ".join(errors))


def _is_transient_llm_error(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message or "1305" in message or "访问量过大" in message


def _request_zhipu_chat_completion_with_model(messages: list[dict], model_name: str) -> str:
    try:
        return request_chat_completion_with_model(messages, model_name)
    except LlmClientError as exc:
        raise IntelligenceGenerationError(str(exc)) from exc


def build_intelligence_system_prompt() -> str:
    return (
        "你是猎头情报分析助手，表达必须正常、直接、清楚，不使用角色扮演、人设口吻或故事化表达。"
        "你只能基于用户提供的结构化输入判断，不能臆造未提供的数据，也不能引用输入里不存在的公司、岗位、人物。"
        "你只能根据 change_context 写今天真正变化的内容；overview、bucket_stats、top_tags 只能作为背景，不能作为主判断。"
        "请直接输出 JSON 对象，不要输出额外解释，不要输出 markdown。"
        "JSON 必须包含 narrative、headline、summary、findings、actions 五个字段。"
        "narrative、headline 和 summary 必须是字符串。findings 和 actions 必须是字符串数组，且各只写 1 条。"
        "narrative 是前端直接显示的主文案，必须是一段 120 到 220 字的情报短报，不是列表，不是报告。"
        "固定结构必须是：先说明今天相对近14天哪里变了；再解释这个变化说明什么；最后说明今天该先盯什么公司类型和岗位类型。"
        "重点必须回答：今天和近14天基线相比，猎场哪里变了；这个变化说明什么；今天更该先盯什么公司类型和岗位类型。"
        "禁止纯统计播报，不能只重复标签次数、公司数量、岗位数量。"
        "禁止报告腔，例如“根据数据分析可得”“本周市场动态显示”“综合来看”。"
        "禁止空泛建议，例如“制定专项方案”“加强关注”“主动接触候选人”。"
        "认领人只表示内部占坑状态，不是联系人，不是候选人，不是行动线索。"
        "禁止引用任何认领人名字，禁止写“联系已报备的人”“利用已报备线索”。"
        "请严格模仿下面这个 JSON 风格，只替换成当前输入对应的内容："
        '{"narrative":"今天先看重新抬头的核心产研岗。和近14天基线相比，今天真正冒头的不是热闹标签，而是更集中地压在高赏金、业务关键、时间压力更高的岗位上。这说明市场不是单纯变热，而是企业更愿意把真正卡节奏的岗位先往外放，尤其是技术、AI和产品里带负责人属性的岗位。下一步更该先盯重点公司和持续招不动的团队，优先看技术、AI、产品里的高赏金核心岗。",'
        '"headline":"今天先看重新抬头的核心产研岗。",'
        '"summary":"和近14天基线相比，今天真正冒头的是高赏金、业务关键、时间压力更高的核心岗位。",'
        '"findings":["这说明企业更愿意把真正卡节奏的岗位先往外放，尤其是技术、AI和产品里带负责人属性的岗位。"],'
        '"actions":["下一步先盯重点公司和持续招不动的团队，优先看技术、AI、产品里的高赏金核心岗。"]}'
    )


def build_intelligence_user_prompt(llm_input: dict) -> str:
    return (
        "请基于下面的统一分析基线生成猎场情报。"
        "必须优先使用 change_context 解释今天相对昨天和近14天基线的变化。"
        "只能根据 change_context 写今天真正变化的是什么，点名 1 到 3 个真正代表变化的公司或岗位方向即可。"
        "job_fact_briefs 只能用于补充证据，不得替代 change_context 做判断。"
        "不要做标签播报，不要写管理建议，不要写联系人动作。"
        "输出时先写好 narrative 这段完整短报，前端会直接显示 narrative 原文。"
        "headline、summary、findings、actions 只是兼容字段，内容必须与 narrative 对齐。"
        "不要写角色化表达或故事化互动。"
        "findings 和 actions 各只写 1 条完整句子。"
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

    if "James侦探" in joined or "酒馆" in joined or "你示意他继续" in joined or "你抬眼示意他继续" in joined:
        raise IntelligenceGenerationError("LLM response used persona framing")

    for name in banned_names:
        if name and name in joined:
            raise IntelligenceGenerationError("LLM response leaked claimed_names")

    for phrase in REPORT_TONE_PHRASES + GENERIC_ACTION_PHRASES:
        if phrase in joined:
            raise IntelligenceGenerationError(f"LLM response used banned phrase: {phrase}")

    if "标签" in joined and ("出现" in joined or "达" in joined):
        raise IntelligenceGenerationError("LLM response fell back to tag count broadcast")


def build_narrative_from_fields(*, headline: str, summary: str, findings: list[str], actions: list[str]) -> str:
    clean_findings = [item.strip() for item in findings if item.strip()]
    clean_actions = [item.strip() for item in actions if item.strip()]
    follow_up = clean_findings[0] if clean_findings else ""

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
