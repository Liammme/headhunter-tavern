import re
from datetime import date, datetime, timedelta
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, MarketIntelligenceSnapshot
from app.services.market_intelligence_report import (
    MarketIntelligenceReportError,
    build_rule_market_report,
    generate_market_report,
)
from app.services.market_signal_builder import build_market_signal_payload


ERROR_MESSAGE_LIMIT = 500
SUCCESS_REFRESH_INTERVAL_DAYS = 3
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


def generate_daily_market_intelligence_snapshot(
    db: Session,
    *,
    snapshot_date: date | None = None,
    clock: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    generated_at = clock().replace(microsecond=0)
    target_date = snapshot_date or generated_at.date()
    recent_success = _load_recent_success_snapshot(db, generated_at=generated_at)
    if recent_success is not None:
        return {"status": "skipped", "snapshot_id": recent_success.id}

    jobs = list(db.execute(select(Job)).scalars().all())
    signal_payload = build_market_signal_payload(jobs=jobs, snapshot_date=target_date)
    if db.in_transaction():
        db.commit()

    try:
        report_payload = generate_market_report(signal_payload)
    except MarketIntelligenceReportError as exc:
        error_message = _sanitize_error_message(exc)
        snapshot = MarketIntelligenceSnapshot(
            snapshot_date=target_date,
            generated_at=generated_at,
            window_days=90,
            market_signal_payload=signal_payload,
            report_payload=build_rule_market_report(signal_payload),
            model_name=None,
            status="fallback",
            error_message=error_message,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return {"status": "fallback", "snapshot_id": snapshot.id}
    except Exception as exc:
        error_message = _sanitize_error_message(exc)
        snapshot = MarketIntelligenceSnapshot(
            snapshot_date=target_date,
            generated_at=generated_at,
            window_days=90,
            market_signal_payload=signal_payload,
            report_payload={},
            model_name=None,
            status="failed",
            error_message=error_message,
        )
        db.add(snapshot)
        db.commit()
        return {"status": "failed", "error": error_message}

    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=target_date,
        generated_at=generated_at,
        window_days=90,
        market_signal_payload=signal_payload,
        report_payload=report_payload,
        model_name=None,
        status="success",
        error_message=None,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": "success", "snapshot_id": snapshot.id}


def _load_recent_success_snapshot(
    db: Session,
    *,
    generated_at: datetime,
) -> MarketIntelligenceSnapshot | None:
    cutoff = generated_at - timedelta(days=SUCCESS_REFRESH_INTERVAL_DAYS)
    return db.execute(
        select(MarketIntelligenceSnapshot)
        .where(
            MarketIntelligenceSnapshot.status == "success",
            MarketIntelligenceSnapshot.generated_at >= cutoff,
        )
        .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _sanitize_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    message = DB_CREDENTIAL_URL_PATTERN.sub("[redacted]", message)
    message = AUTHORIZATION_BEARER_PATTERN.sub("Authorization: Bearer [redacted]", message)
    message = OPENAI_KEY_PATTERN.sub("[redacted]", message)
    message = KEY_VALUE_SECRET_PATTERN.sub(_redact_key_value_secret, message)
    return message[:ERROR_MESSAGE_LIMIT]


def _redact_key_value_secret(match: re.Match) -> str:
    separator = match.group(2)
    if separator == ":":
        return f"{match.group(1)}: [redacted]"
    return f"{match.group(1)}=[redacted]"
