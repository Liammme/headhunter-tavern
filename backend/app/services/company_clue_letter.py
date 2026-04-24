import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job
from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue
from app.services.company_clue_prompt import build_company_clue_messages, build_company_clue_rewrite_messages
from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import IntelligenceGenerationError, request_zhipu_structured_json

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
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company clue generation unavailable",
            narrative=f"{company} 的单公司线索来信当前不可用，请稍后再试。",
        )

    context = build_company_clue_context(company=company, jobs=jobs, today=now.date())
    try:
        payload = _request_and_validate(context)
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
