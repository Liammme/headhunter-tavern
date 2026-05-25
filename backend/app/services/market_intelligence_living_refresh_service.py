from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.services.japan_market_profile import JAPAN_RECRUITING_MARKET_PROFILE
from app.services.market_intelligence_fact_service import backfill_market_intelligence_facts
from app.services.market_intelligence_living_report_service import (
    generate_living_market_report,
    load_latest_success_living_snapshot,
)
from app.services.region import GLOBAL_REGION, JAPAN_REGION, RegionCode
from app.services.talentverse_report_generation import (
    generate_talentverse_report_for_snapshot,
    sanitize_talentverse_error,
)


def refresh_living_market_report_if_due(
    db: Session,
    *,
    days: int = 180,
    min_age_days: int = 3,
    clock: Callable[[], datetime] = datetime.now,
    region: RegionCode = GLOBAL_REGION,
    adapters=None,
) -> dict:
    generated_at = clock().replace(microsecond=0)
    fact_summary = backfill_market_intelligence_facts(
        db,
        days=days,
        dry_run=False,
        collected_at=generated_at,
        region=region,
        adapters=adapters,
    )

    report_profile = JAPAN_RECRUITING_MARKET_PROFILE if region == JAPAN_REGION else None
    latest = load_latest_success_living_snapshot(db, region=region, report_profile=report_profile)
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
        region=region,
    )
    if result.get("status") == "success" and region == GLOBAL_REGION:
        snapshot_id = result.get("snapshot_id")
        if isinstance(snapshot_id, int):
            try:
                result["talentverse_report"] = generate_talentverse_report_for_snapshot(
                    db,
                    raw_snapshot_id=snapshot_id,
                )
            except Exception as exc:  # noqa: BLE001
                result["talentverse_report"] = {
                    "status": "failed",
                    "error": sanitize_talentverse_error(exc),
                }
    result["facts"] = fact_summary
    return result
