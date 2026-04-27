import logging
import copy
import hashlib
import json
import time
from collections import OrderedDict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Job
from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue
from app.services.company_clue_prompt import build_company_clue_messages, build_company_clue_rewrite_messages
from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import IntelligenceGenerationError, request_zhipu_structured_json
from app.services.llm_client import should_use_llm

logger = logging.getLogger(__name__)
COMPANY_CLUE_CACHE_MAX_ENTRIES = 128
_company_clue_cache: OrderedDict[str, dict] = OrderedDict()


def generate_company_clue_letter(db: Session, *, company: str) -> dict:
    started_at = time.perf_counter()
    now = datetime.now().replace(microsecond=0)
    jobs = load_company_jobs_for_clue(db, company=company, today=now.date())
    _log_company_clue_timing(company=company, phase="load_jobs", started_at=started_at, job_count=len(jobs))
    generated_at = _resolve_generated_at(jobs, fallback=now)

    if not jobs:
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company not found",
            narrative=f"{company} 的单公司线索来信当前无法生成，因为统一 14 天基线里没有这家公司的精确匹配资料。",
        )

    context_started_at = time.perf_counter()
    context = build_company_clue_context(company=company, jobs=jobs, today=now.date())
    _log_company_clue_timing(company=company, phase="build_context", started_at=context_started_at, job_count=len(jobs))

    if not _should_use_company_clue_llm():
        payload = _build_rule_company_clue_payload(context)
        return {
            "status": "success",
            "company": company,
            "generated_at": generated_at,
            "narrative": payload["narrative"],
            "sections": payload["sections"],
            "error_message": None,
        }

    cache_key = _build_company_clue_cache_key(company=company, jobs=jobs)
    cached = _read_company_clue_cache(cache_key)
    if cached is not None:
        _log_company_clue_timing(company=company, phase="cache_hit", started_at=started_at, job_count=len(jobs))
        return cached

    try:
        llm_started_at = time.perf_counter()
        payload = _request_and_validate(context)
        _log_company_clue_timing(company=company, phase="llm_generate", started_at=llm_started_at, job_count=len(jobs))
    except Exception as exc:
        logger.warning("Failed to generate company clue letter for %s: %s", company, exc)
        payload = _build_rule_company_clue_payload(context)
        return {
            "status": "success",
            "company": company,
            "generated_at": generated_at,
            "narrative": payload["narrative"],
            "sections": payload["sections"],
            "error_message": None,
        }

    result = {
        "status": "success",
        "company": company,
        "generated_at": generated_at,
        "narrative": payload["narrative"],
        "sections": payload["sections"],
        "error_message": None,
    }
    _write_company_clue_cache(cache_key, result)
    _log_company_clue_timing(company=company, phase="total", started_at=started_at, job_count=len(jobs))
    return result


def _request_and_validate(context: dict) -> dict:
    first_started_at = time.perf_counter()
    first_response = request_zhipu_structured_json(build_company_clue_messages(context))
    logger.info("Company clue LLM first pass finished in %.0fms", _elapsed_ms(first_started_at))
    try:
        validate_started_at = time.perf_counter()
        parsed = parse_company_clue_response(first_response)
        validate_company_clue_response(parsed, context=context)
        logger.info("Company clue validation finished in %.0fms", _elapsed_ms(validate_started_at))
        return parsed
    except IntelligenceGenerationError as exc:
        repair_started_at = time.perf_counter()
        repaired_response = request_zhipu_structured_json(
            build_company_clue_rewrite_messages(
                context=context,
                invalid_content=first_response,
                validation_error=str(exc),
            )
        )
        logger.info("Company clue LLM repair pass finished in %.0fms", _elapsed_ms(repair_started_at))
        repaired = parse_company_clue_response(repaired_response)
        validate_company_clue_response(repaired, context=context)
        return repaired


def _resolve_generated_at(jobs: list[Job], *, fallback: datetime) -> str:
    if jobs:
        latest = jobs[0].collected_at.replace(microsecond=0)
        return latest.isoformat()
    return fallback.isoformat()


def _should_use_company_clue_llm() -> bool:
    return should_use_llm()


def _build_rule_company_clue_payload(context: dict) -> dict:
    company = context["company"]
    summary = context.get("summary", {})
    evidence_cards = list(context.get("evidence_cards") or [])
    entry_points = context.get("entry_points") or {}
    titles = [card["title"] for card in evidence_cards if card.get("title")]
    title_text = "、".join(titles[:3]) if titles else "当前岗位"
    top_categories = "、".join(summary.get("top_categories") or []) or "核心"
    top_domains = "、".join(summary.get("top_domains") or []) or "重点领域"
    first_entry = _first_entry_point(entry_points)

    narrative = (
        f"{company} 在当前 14 天窗口内有 {summary.get('total_jobs', len(evidence_cards))} 个岗位，"
        f"主要集中在 {top_categories} / {top_domains}。"
        f"其中 {title_text} 是最直接的岗位证据，说明这家公司当前至少有一条可追踪的招聘入口。"
        f"下一步先回到真实岗位入口核对职责、发布时间和团队方向，再决定是否优先摸排。"
    )
    return {
        "narrative": narrative,
        "sections": [
            {
                "key": "clue_1",
                "title": "线索一：需求信号",
                "content": (
                    f"{company} 当前窗口内共有 {summary.get('total_jobs', len(evidence_cards))} 个岗位，"
                    f"集中在 {top_categories} / {top_domains}，说明需求不是完全零散出现。"
                ),
            },
            {
                "key": "clue_2",
                "title": "线索二：关键岗位",
                "content": f"{title_text} 是当前最值得先核对的岗位证据。",
            },
            {
                "key": "clue_3",
                "title": "线索三：行动入口",
                "content": f"先回到 {first_entry} 核对岗位职责、发布时间和团队方向，再判断是否优先切入。",
            },
        ],
    }


def _first_entry_point(entry_points: dict) -> str:
    for key in ("job_posts", "hiring_pages", "company_urls", "emails"):
        values = entry_points.get(key) or []
        if values:
            return values[0]
    return "当前公司公开岗位入口"


def _build_failure_response(*, company: str, generated_at: str, error_message: str, narrative: str) -> dict:
    return {
        "status": "failure",
        "company": company,
        "generated_at": generated_at,
        "narrative": narrative,
        "sections": [],
        "error_message": error_message,
    }


def _build_company_clue_cache_key(*, company: str, jobs: list[Job]) -> str:
    fingerprint = {
        "company": company,
        "jobs": [
            {
                "id": job.id,
                "canonical_url": job.canonical_url,
                "title": job.title,
                "posted_at": _datetime_fingerprint(job.posted_at),
                "collected_at": _datetime_fingerprint(job.collected_at),
                "bounty_grade": job.bounty_grade,
                "signal_tags": job.signal_tags if isinstance(job.signal_tags, dict) else {},
            }
            for job in jobs
        ],
    }
    serialized = json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_company_clue_cache(cache_key: str) -> dict | None:
    cached = _company_clue_cache.get(cache_key)
    if cached is None:
        return None
    _company_clue_cache.move_to_end(cache_key)
    return copy.deepcopy(cached)


def _write_company_clue_cache(cache_key: str, result: dict) -> None:
    _company_clue_cache[cache_key] = copy.deepcopy(result)
    _company_clue_cache.move_to_end(cache_key)
    while len(_company_clue_cache) > COMPANY_CLUE_CACHE_MAX_ENTRIES:
        _company_clue_cache.popitem(last=False)


def _datetime_fingerprint(value: datetime | None) -> str | None:
    return value.replace(microsecond=0).isoformat() if value else None


def _log_company_clue_timing(*, company: str, phase: str, started_at: float, job_count: int) -> None:
    logger.info(
        "Company clue generation phase=%s company=%s job_count=%s duration_ms=%.0f",
        phase,
        company,
        job_count,
        _elapsed_ms(started_at),
    )


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000
