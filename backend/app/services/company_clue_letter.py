import json
import logging
import re
from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job
from app.services.bounty_estimation import BountyEstimate
from app.services.intelligence import IntelligenceGenerationError, request_zhipu_structured_json
from app.services.job_facts import StandardizedJobInput, build_v2_score_input, extract_job_facts
from app.services.scoring import score_job_v2

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def generate_company_clue_letter(db: Session, *, company: str) -> dict:
    jobs = _load_company_jobs_exact(db, company)
    generated_at = _resolve_generated_at(jobs)

    if not jobs:
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company not found",
            narrative=f"{company} 的单公司线索来信当前无法生成，因为系统内没有这家公司的精确匹配资料。",
        )

    if not _should_use_company_clue_llm():
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company clue generation unavailable",
            narrative=f"{company} 的单公司线索来信当前不可用，请稍后再试。",
        )

    llm_input = build_company_clue_llm_input(company=company, jobs=jobs)
    messages = [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {"role": "user", "content": build_company_clue_user_prompt(llm_input)},
    ]

    try:
        response_content = request_zhipu_structured_json(messages)
        parsed = parse_company_clue_response(response_content)
    except Exception as exc:
        logger.warning("Failed to generate company clue letter for %s: %s", company, exc)
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company clue generation failed",
            narrative=f"{company} 的单公司线索来信生成失败，请稍后重试。",
        )

    return {
        "status": "success",
        "company": company,
        "generated_at": generated_at,
        "narrative": parsed["narrative"],
        "sections": parsed["sections"],
        "error_message": None,
    }


def build_company_clue_llm_input(*, company: str, jobs: list[Job]) -> dict:
    job_brief_pairs = [(job, _build_job_brief(job)) for job in jobs]
    job_briefs = [brief for _job, brief in job_brief_pairs]
    sorted_job_brief_pairs = sorted(job_brief_pairs, key=lambda item: _job_brief_sort_key(item[1]))
    sorted_briefs = [brief for _job, brief in sorted_job_brief_pairs]
    categories = Counter(item["category"] for item in job_briefs)
    domains = Counter(item["domain_tag"] for item in job_briefs)

    return {
        "company_summary": {
            "company": company,
            "total_jobs": len(jobs),
            "high_bounty_jobs": sum(1 for item in job_briefs if item["bounty_grade"] == "high"),
            "urgent_jobs": sum(1 for item in job_briefs if "urgent" in item["time_pressure_signals"]),
            "critical_jobs": sum(1 for item in job_briefs if item["critical"]),
            "top_categories": [name for name, _count in categories.most_common(3)],
            "top_domains": [name for name, _count in domains.most_common(2)],
            "estimated_bounty": _collect_estimated_bounty([job for job, _brief in sorted_job_brief_pairs]),
        },
        "highlighted_jobs": sorted_briefs[:3],
        "entry_points": _collect_entry_points(jobs),
    }


def build_company_clue_system_prompt() -> str:
    return (
        "你是 James侦探，正在给某一家公司的单公司线索来信。"
        "你只能依据用户给你的结构化输入判断，不能编造不存在的公司信息、岗位信息、联系人或外部资料。"
        "请直接输出 JSON 对象，不要输出 markdown，不要解释。"
        "JSON 必须包含 narrative 和 sections 两个字段。"
        "narrative 必须是字符串，长度控制在 180 到 320 字。"
        "sections 必须是 3 个对象组成的数组，每个对象都必须包含 key、title、content。"
        "三个 section 的 key 固定为 lead、evidence、next_move。"
        "口吻要保留 James侦探 的判断感，但重点是把这家公司为什么值得先查、哪些岗位最关键、下一步该盯什么说清楚。"
        "不要写成首页情报，不要总结全市场，不要引用输入里没有的邮箱、官网或岗位。"
    )


def build_company_clue_user_prompt(llm_input: dict) -> str:
    return (
        "请基于下面这家公司的结构化线索生成单公司来信。"
        "必须只围绕这一家公司，不要扩展到全市场。"
        "优先利用 company_summary、highlighted_jobs、entry_points 解释："
        "1) 这家公司为什么值得先查；"
        "2) 哪 2 到 3 个岗位最能代表线索强度；"
        "3) 如果用户要继续推进，下一步该盯哪些入口和信号。"
        "如果 estimated_bounty 有值，可以点出预计赏金；没有就不要编造。"
        "sections 的三个标题请分别写成“我先看到的”“这家公司现在露出的口子”“你下一步怎么查”。"
        f"\n\n结构化输入：\n{json.dumps(llm_input, ensure_ascii=False)}"
    )


def parse_company_clue_response(content: str) -> dict:
    normalized_content = _strip_code_fence(content)
    try:
        payload = json.loads(normalized_content)
    except json.JSONDecodeError as exc:
        raise IntelligenceGenerationError("Company clue response is not valid JSON") from exc

    narrative = payload.get("narrative")
    sections = payload.get("sections")
    if not isinstance(narrative, str) or not narrative.strip():
        raise IntelligenceGenerationError("Company clue response is missing narrative")
    if not isinstance(sections, list) or len(sections) != 3:
        raise IntelligenceGenerationError("Company clue response must contain three sections")

    normalized_sections: list[dict] = []
    for expected_key, section in zip(("lead", "evidence", "next_move"), sections):
        if not isinstance(section, dict):
            raise IntelligenceGenerationError("Company clue section must be an object")
        key = section.get("key")
        title = section.get("title")
        section_content = section.get("content")
        if key != expected_key:
            raise IntelligenceGenerationError("Company clue section keys are invalid")
        if not isinstance(title, str) or not title.strip():
            raise IntelligenceGenerationError("Company clue section is missing title")
        if not isinstance(section_content, str) or not section_content.strip():
            raise IntelligenceGenerationError("Company clue section is missing content")
        normalized_sections.append(
            {"key": key, "title": title.strip(), "content": section_content.strip()}
        )

    return {"narrative": narrative.strip(), "sections": normalized_sections}


def _build_job_brief(job: Job) -> dict:
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
    return {
        "title": job.title,
        "bounty_grade": job.bounty_grade,
        "category": facts.category,
        "domain_tag": facts.domain_tag,
        "seniority": facts.seniority,
        "critical": facts.critical,
        "time_pressure_signals": list(facts.time_pressure_signals),
        "anomaly_signals": list(facts.anomaly_signals),
        "business_criticality": facts.business_criticality,
        "v2_reasons": list(score_result.reasons),
        "rule_hits": [hit.code for hit in score_result.rule_hits],
        "entry_points": {
            "job_post": job.canonical_url,
            "company_url": _read_signal_tag(job, "company_url"),
            "hiring_page": _read_signal_tag(job, "hiring_page_url", "apply_url"),
            "email": _extract_email(job),
        },
    }


def _job_brief_sort_key(brief: dict) -> tuple:
    return (
        {"high": 0, "medium": 1, "low": 2}.get(brief["bounty_grade"], 3),
        -len(brief["time_pressure_signals"]),
        -len(brief["anomaly_signals"]),
        {"high": 0, "medium": 1, "low": 2}.get(brief["business_criticality"], 3),
        brief["title"].lower(),
    )


def _collect_entry_points(jobs: list[Job]) -> dict:
    company_urls = _dedupe_non_empty(_read_signal_tag(job, "company_url") for job in jobs)
    hiring_pages = _dedupe_non_empty(_read_signal_tag(job, "hiring_page_url", "apply_url") for job in jobs)
    job_posts = _dedupe_non_empty(job.canonical_url for job in jobs)
    emails = _dedupe_non_empty(_extract_email(job) for job in jobs)
    return {
        "company_urls": company_urls[:3],
        "hiring_pages": hiring_pages[:3],
        "job_posts": job_posts[:5],
        "emails": emails[:3],
    }


def _collect_estimated_bounty(jobs: list[Job]) -> dict | None:
    for job in jobs:
        estimate = BountyEstimate.from_signal_tags(job.signal_tags if isinstance(job.signal_tags, dict) else None)
        if estimate is not None:
            return {"amount": estimate.amount, "label": estimate.label}
    return None


def _load_company_jobs_exact(db: Session, company: str) -> list[Job]:
    return (
        db.query(Job)
        .filter(Job.company == company)
        .order_by(Job.collected_at.desc(), Job.id.desc())
        .all()
    )


def _resolve_generated_at(jobs: list[Job]) -> str:
    if jobs:
        latest = jobs[0].collected_at.replace(microsecond=0)
        return latest.isoformat()
    return datetime.now().replace(microsecond=0).isoformat()


def _should_use_company_clue_llm() -> bool:
    return settings.bounty_pool_intelligence_llm_enabled and bool(settings.bounty_pool_zhipu_api_key)


def _build_failure_response(*, company: str, generated_at: str, error_message: str, narrative: str) -> dict:
    return {
        "status": "failure",
        "company": company,
        "generated_at": generated_at,
        "narrative": narrative,
        "sections": [],
        "error_message": error_message,
    }


def _read_signal_tag(job: Job, *keys: str) -> str | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    for key in keys:
        value = signal_tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_email(job: Job) -> str | None:
    match = EMAIL_PATTERN.search(job.description or "")
    if match is None:
        return None
    return match.group(0)


def _dedupe_non_empty(values) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if not value or value in deduped:
            continue
        deduped.append(value)
    return deduped


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
