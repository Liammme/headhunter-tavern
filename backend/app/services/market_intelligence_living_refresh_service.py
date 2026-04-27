from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.services.market_intelligence_fact_service import backfill_market_intelligence_facts
from app.services.market_intelligence_living_report_service import (
    generate_living_market_report,
    load_latest_success_living_snapshot,
)


def refresh_living_market_report_if_due(
    db: Session,
    *,
    days: int = 180,
    min_age_days: int = 3,
    clock: Callable[[], datetime] = datetime.now,
) -> dict:
    generated_at = clock().replace(microsecond=0)
    fact_summary = backfill_market_intelligence_facts(
        db,
        days=days,
        dry_run=False,
        collected_at=generated_at,
    )

    latest = load_latest_success_living_snapshot(db)
    if latest is not None:
        next_due_date = latest.generated_at.date() + timedelta(days=min_age_days)
        next_due_at = datetime.combine(next_due_date, generated_at.time())
        if generated_at < next_due_at:
            return {
                "status": "skipped",
                "reason": "latest_success_fresh",
                "latest_snapshot_id": latest.id,
                "latest_generated_at": latest.generated_at.replace(microsecond=0).isoformat(),
                "next_due_at": next_due_at.isoformat(),
                "facts": fact_summary,
            }

    result = generate_living_market_report(
        db,
        mode="auto",
        days=days,
        snapshot_date=generated_at.date(),
        clock=lambda: generated_at,
    )
    result["facts"] = fact_summary
    return result
