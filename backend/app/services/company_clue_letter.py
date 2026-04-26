import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Job
from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue
from app.services.company_clue_prompt import build_company_clue_messages, build_company_clue_rewrite_messages
from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import IntelligenceGenerationError, request_zhipu_structured_json
from app.services.llm_client import should_use_llm

logger = logging.getLogger(__name__)


def generate_company_clue_letter(db: Session, *, company: str) -> dict:
    now = datetime.now().replace(microsecond=0)
    jobs = load_company_jobs_for_clue(db, company=company, today=now.date())
    generated_at = _resolve_generated_at(jobs, fallback=now)

    if not jobs:
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company not found",
            narrative=f"{company} 的单公司线索来信当前无法生成，因为统一 14 天基线里没有这家公司的精确匹配资料。",
        )

    if not _should_use_company_clue_llm():
        context = build_company_clue_context(company=company, jobs=jobs, today=now.date())
        payload = _build_rule_company_clue_payload(context)
        return {
            "status": "success",
            "company": company,
            "generated_at": generated_at,
            "narrative": payload["narrative"],
            "sections": payload["sections"],
            "error_message": None,
        }

    context = build_company_clue_context(company=company, jobs=jobs, today=now.date())
    try:
        payload = _request_and_validate(context)
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

    return {
        "status": "success",
        "company": company,
        "generated_at": generated_at,
        "narrative": payload["narrative"],
        "sections": payload["sections"],
        "error_message": None,
    }


def _request_and_validate(context: dict) -> dict:
    first_response = request_zhipu_structured_json(build_company_clue_messages(context))
    try:
        parsed = parse_company_clue_response(first_response)
        validate_company_clue_response(parsed, context=context)
        return parsed
    except IntelligenceGenerationError as exc:
        repaired_response = request_zhipu_structured_json(
            build_company_clue_rewrite_messages(
                context=context,
                invalid_content=first_response,
                validation_error=str(exc),
            )
        )
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
