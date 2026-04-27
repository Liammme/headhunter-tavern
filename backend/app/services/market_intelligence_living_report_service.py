from datetime import date, datetime
from typing import Callable, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot
from app.services.market_intelligence_living_payload import build_living_market_report_input
from app.services.market_intelligence_living_report import (
    build_rule_living_market_report,
    generate_living_market_report_payload,
    validate_living_market_report,
)
from app.services.market_intelligence_snapshot_service import _sanitize_error_message

Mode = Literal["baseline", "update", "auto"]


def generate_living_market_report(
    db: Session,
    *,
    mode: Mode,
    days: int = 180,
    snapshot_date: date | None = None,
    clock: Callable[[], datetime] = datetime.now,
) -> dict:
    generated_at = clock().replace(microsecond=0)
    target_date = snapshot_date or generated_at.date()
    previous_snapshot = _load_latest_success_living_snapshot(db)
    resolved_mode = "baseline" if mode == "auto" and previous_snapshot is None else mode
    if resolved_mode == "auto":
        resolved_mode = "update"
    if resolved_mode == "update" and previous_snapshot is None:
        raise ValueError("update requires a previous successful living report")

    version = 1 if resolved_mode == "baseline" else _living_version(previous_snapshot) + 1
    living_mode = "baseline_seed" if resolved_mode == "baseline" else "incremental_update"
    input_payload = build_living_market_report_input(
        db,
        mode=resolved_mode,
        days=days,
        snapshot_date=target_date,
        previous_snapshot=previous_snapshot if resolved_mode == "update" else None,
    )
    input_payload["fact_watermark"] = _fact_watermark(input_payload)

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
        snapshot_date=target_date,
        generated_at=generated_at,
        window_days=days,
        market_signal_payload=input_payload,
        report_payload=_compat_report_payload(living_report),
        model_name=None,
        status=status,
        error_message=error_message,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": status, "snapshot_id": snapshot.id}


def _compat_report_payload(living_report: dict) -> dict:
    return {
        "headline": "活报告已更新",
        "narrative": living_report.get("executive_summary", ""),
        "primary_judgment": {
            "claim": living_report.get("executive_summary", ""),
            "why_it_matters": "用于首页读取兼容。",
            "confidence": "low",
        },
        "perspectives": [],
        "trend_cards": [],
        "watchlist": [],
        "living_report": living_report,
    }


def _load_latest_success_living_snapshot(db: Session) -> MarketIntelligenceSnapshot | None:
    snapshots = (
        db.execute(
            select(MarketIntelligenceSnapshot)
            .where(MarketIntelligenceSnapshot.status == "success")
            .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    for snapshot in snapshots:
        report = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
        living = report.get("living_report")
        if isinstance(living, dict) and living.get("kind") == "living_market_report":
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
