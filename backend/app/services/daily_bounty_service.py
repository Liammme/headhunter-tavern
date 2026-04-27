import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.services.crawl_trigger_service import trigger_crawl
from app.services.home_query_service import get_home_payload
from app.services.market_intelligence_snapshot_service import generate_daily_market_intelligence_snapshot


DB_CREDENTIAL_URL_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@[^\s]+",
    re.IGNORECASE,
)
OPENAI_KEY_PATTERN = re.compile(r"sk-[^\s,;]+", re.IGNORECASE)
KEY_VALUE_SECRET_PATTERN = re.compile(
    r"\b([a-z0-9_]*(?:api_key|token|password))\s*([=:])\s*([^\s,;]+)",
    re.IGNORECASE,
)
AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\bAuthorization\s*:\s*Bearer\s+[^\s,;]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DailyBountySummary:
    status: str
    started_at: str
    finished_at: str
    fetched_jobs: int
    new_jobs: int
    source_stats: dict[str, int]
    errors: list[str]
    recent_3_day_company_count: int
    recent_3_day_job_count: int


def run_daily_bounty_generation(
    db: Session,
    *,
    clock: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    started_at = _isoformat(clock())
    crawl_result: dict[str, Any] = {
        "fetched_jobs": 0,
        "new_jobs": 0,
        "source_stats": {},
        "errors": [],
    }

    try:
        crawl_result = trigger_crawl(db)
        errors = [_sanitize_error_message(error) for error in crawl_result.get("errors") or []]
        status = "completed_with_errors" if errors else "completed"
        try:
            snapshot_result = generate_daily_market_intelligence_snapshot(db)
            if snapshot_result.get("status") == "failed":
                error = _sanitize_error_message(snapshot_result.get("error") or "unknown error")
                errors.append(f"market_intelligence: {error}")
                if status == "completed":
                    status = "completed_with_errors"
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            errors.append(f"market_intelligence: {_sanitize_error_message(exc)}")
            if status == "completed":
                status = "completed_with_errors"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        errors = [f"daily_bounty: {_sanitize_error_message(exc)}"]
        status = "failed"

    home_payload = get_home_payload(db)
    recent_3_day_company_count, recent_3_day_job_count = _summarize_recent_3_days(home_payload)
    finished_at = _isoformat(clock())

    summary = DailyBountySummary(
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        fetched_jobs=int(crawl_result.get("fetched_jobs") or 0),
        new_jobs=int(crawl_result.get("new_jobs") or 0),
        source_stats=dict(crawl_result.get("source_stats") or {}),
        errors=errors,
        recent_3_day_company_count=recent_3_day_company_count,
        recent_3_day_job_count=recent_3_day_job_count,
    )
    return asdict(summary)


def _summarize_recent_3_days(home_payload: dict[str, Any]) -> tuple[int, int]:
    recent_bucket = next(
        (day for day in home_payload.get("days", []) if day.get("bucket") == "within_3_days"),
        None,
    )
    if not recent_bucket:
        return 0, 0

    companies = list(recent_bucket.get("companies") or [])
    job_count = sum(_company_job_count(company) for company in companies)
    return len(companies), job_count


def _company_job_count(company: dict[str, Any]) -> int:
    if "total_jobs" in company:
        return int(company["total_jobs"] or 0)
    return len(company.get("jobs") or [])


def _isoformat(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _sanitize_error_message(error: Any) -> str:
    message = str(error) or error.__class__.__name__
    message = DB_CREDENTIAL_URL_PATTERN.sub("[redacted]", message)
    message = AUTHORIZATION_BEARER_PATTERN.sub("Authorization: Bearer [redacted]", message)
    message = OPENAI_KEY_PATTERN.sub("[redacted]", message)
    message = KEY_VALUE_SECRET_PATTERN.sub(_redact_key_value_secret, message)
    return message


def _redact_key_value_secret(match: re.Match) -> str:
    separator = match.group(2)
    if separator == ":":
        return f"{match.group(1)}: [redacted]"
    return f"{match.group(1)}=[redacted]"
