from datetime import date, datetime
from typing import Callable, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot
from app.services.japan_living_report_payload import build_japan_living_market_report_input
from app.services.japan_market_profile import JAPAN_RECRUITING_MARKET_PROFILE
from app.services.market_intelligence_living_payload import build_living_market_report_input
from app.services.market_intelligence_living_report import (
    build_rule_living_market_report,
    generate_living_market_report_payload,
    validate_living_market_report,
)
from app.services.market_intelligence_snapshot_service import _sanitize_error_message
from app.services.region import GLOBAL_REGION, JAPAN_REGION, RegionCode

Mode = Literal["baseline", "update", "auto"]
LIVING_SNAPSHOT_SCAN_BATCH_SIZE = 50
LIVING_SNAPSHOT_SCAN_MAX_BATCHES = 20


def generate_living_market_report(
    db: Session,
    *,
    mode: Mode,
    days: int = 180,
    snapshot_date: date | None = None,
    clock: Callable[[], datetime] = datetime.now,
    force: bool = False,
    region: RegionCode = GLOBAL_REGION,
) -> dict:
    generated_at = clock().replace(microsecond=0)
    target_date = snapshot_date or generated_at.date()
    report_profile = JAPAN_RECRUITING_MARKET_PROFILE if region == JAPAN_REGION else None
    previous_snapshot = load_latest_success_living_snapshot(db, region=region, report_profile=report_profile)
    resolved_mode = "baseline" if mode == "auto" and previous_snapshot is None else mode
    if resolved_mode == "auto":
        resolved_mode = "update"
    if resolved_mode == "baseline" and previous_snapshot is not None and not force:
        raise ValueError("baseline living report already exists; use force to regenerate")
    if resolved_mode == "update" and previous_snapshot is None:
        raise ValueError("update requires a previous successful living report")

    version = 1 if resolved_mode == "baseline" else _living_version(previous_snapshot) + 1
    living_mode = "baseline_seed" if resolved_mode == "baseline" else "incremental_update"
    input_payload = _build_living_input(
        db,
        mode=resolved_mode,
        days=days,
        snapshot_date=target_date,
        previous_snapshot=previous_snapshot if resolved_mode == "update" else None,
        region=region,
    )
    input_payload["region"] = region
    input_payload["fact_watermark"] = input_payload.get("fact_watermark") or _fact_watermark(input_payload)

    try:
        living_report = generate_living_market_report_payload(
            input_payload,
            version=version,
            mode=living_mode,
            previous_snapshot_id=previous_snapshot.id if previous_snapshot is not None and resolved_mode == "update" else None,
            generated_at=generated_at,
        )
        validate_living_market_report(living_report, input_payload=input_payload, expected_version=version)
        status = "success"
        error_message = None
    except Exception as exc:
        error_message = _sanitize_error_message(exc)
        living_report = build_rule_living_market_report(
            input_payload,
            version=version,
            mode=living_mode,
            previous_snapshot_id=previous_snapshot.id if previous_snapshot is not None and resolved_mode == "update" else None,
            generated_at=generated_at,
        )
        status = "fallback"

    snapshot = MarketIntelligenceSnapshot(
        region=region,
        snapshot_date=target_date,
        generated_at=generated_at,
        window_days=days,
        market_signal_payload=input_payload,
        report_payload=_compat_report_payload(living_report, region=region),
        model_name=None,
        status=status,
        error_message=error_message,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": status, "snapshot_id": snapshot.id}


def _compat_report_payload(living_report: dict, *, region: RegionCode) -> dict:
    headline_fallback = "活报告已更新"
    why_it_matters = "用于首页读取兼容。"
    if region == JAPAN_REGION:
        headline_fallback = "レポートを更新しました"
        why_it_matters = "ホーム画面で読み取るための互換フィールドです。"
    return {
        "region": region,
        "headline": living_report.get("headline") or headline_fallback,
        "narrative": living_report.get("executive_summary", ""),
        "primary_judgment": {
            "claim": living_report.get("executive_summary", ""),
            "why_it_matters": why_it_matters,
            "confidence": "low",
        },
        "perspectives": [],
        "trend_cards": [],
        "watchlist": [],
        "living_report": living_report,
    }


def _build_living_input(
    db: Session,
    *,
    mode: str,
    days: int,
    snapshot_date: date,
    previous_snapshot: MarketIntelligenceSnapshot | None,
    region: RegionCode,
) -> dict:
    if region == JAPAN_REGION:
        return build_japan_living_market_report_input(
            db,
            mode=mode,
            days=days,
            snapshot_date=snapshot_date,
            previous_snapshot=previous_snapshot,
        )
    return build_living_market_report_input(
        db,
        mode=mode,
        days=days,
        snapshot_date=snapshot_date,
        previous_snapshot=previous_snapshot,
        region=region,
    )


def load_latest_success_living_snapshot(
    db: Session,
    *,
    region: RegionCode = GLOBAL_REGION,
    report_profile: str | None = None,
) -> MarketIntelligenceSnapshot | None:
    for batch_index in range(LIVING_SNAPSHOT_SCAN_MAX_BATCHES):
        snapshots = (
            db.execute(
                select(MarketIntelligenceSnapshot)
                .where(MarketIntelligenceSnapshot.status == "success", MarketIntelligenceSnapshot.region == region)
                .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
                .limit(LIVING_SNAPSHOT_SCAN_BATCH_SIZE)
                .offset(batch_index * LIVING_SNAPSHOT_SCAN_BATCH_SIZE)
            )
            .scalars()
            .all()
        )
        if not snapshots:
            return None
        for snapshot in snapshots:
            report = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
            living = report.get("living_report")
            signal_payload = snapshot.market_signal_payload if isinstance(snapshot.market_signal_payload, dict) else {}
            if (
                isinstance(living, dict)
                and living.get("kind") == "living_market_report"
                and (report_profile is None or signal_payload.get("report_profile") == report_profile)
            ):
                return snapshot
    return None


def _living_version(snapshot: MarketIntelligenceSnapshot | None) -> int:
    if snapshot is None:
        return 0
    report = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
    living = report.get("living_report")
    if isinstance(living, dict) and isinstance(living.get("version"), int):
        return living["version"]
    return 0


def _fact_watermark(input_payload: dict) -> dict:
    newest: tuple[str, int] | None = None
    samples = input_payload.get("representative_samples")
    if isinstance(samples, list):
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            created_at = sample.get("created_at")
            fact_id = sample.get("fact_id")
            if isinstance(created_at, str) and isinstance(fact_id, int):
                candidate = (created_at, fact_id)
                if newest is None or candidate > newest:
                    newest = candidate
    if newest is None:
        return {"created_at": datetime.min.isoformat(), "id": 0}
    return {"created_at": newest[0], "id": newest[1]}
