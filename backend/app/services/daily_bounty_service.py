from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.services.crawl_trigger_service import trigger_crawl
from app.services.home_query_service import get_home_payload


@dataclass(frozen=True)
class DailyBountySummary:
    status: str
    started_at: str
    finished_at: str
    fetched_jobs: int
    new_jobs: int
    source_stats: dict[str, int]
    errors: list[str]
    today_company_count: int
    today_job_count: int


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
        errors = list(crawl_result.get("errors") or [])
        status = "completed_with_errors" if errors else "completed"
    except Exception as exc:  # noqa: BLE001
        errors = [f"daily_bounty: {exc}"]
        status = "failed"

    home_payload = get_home_payload(db)
    today_company_count, today_job_count = _summarize_today(home_payload)
    finished_at = _isoformat(clock())

    summary = DailyBountySummary(
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        fetched_jobs=int(crawl_result.get("fetched_jobs") or 0),
        new_jobs=int(crawl_result.get("new_jobs") or 0),
        source_stats=dict(crawl_result.get("source_stats") or {}),
        errors=errors,
        today_company_count=today_company_count,
        today_job_count=today_job_count,
    )
    return asdict(summary)


def _summarize_today(home_payload: dict[str, Any]) -> tuple[int, int]:
    today_bucket = next(
        (day for day in home_payload.get("days", []) if day.get("bucket") == "today"),
        None,
    )
    if not today_bucket:
        return 0, 0

    companies = list(today_bucket.get("companies") or [])
    job_count = sum(_company_job_count(company) for company in companies)
    return len(companies), job_count


def _company_job_count(company: dict[str, Any]) -> int:
    if "total_jobs" in company:
        return int(company["total_jobs"] or 0)
    return len(company.get("jobs") or [])


def _isoformat(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()
