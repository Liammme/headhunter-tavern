import re
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, MarketIntelligenceSnapshot
from app.services.market_intelligence_report import generate_market_report
from app.services.market_signal_builder import build_market_signal_payload


ERROR_MESSAGE_LIMIT = 500
DB_CREDENTIAL_URL_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@[^\s]+",
    re.IGNORECASE,
)
OPENAI_KEY_PATTERN = re.compile(r"sk-[^\s,;]+", re.IGNORECASE)
KEY_VALUE_SECRET_PATTERN = re.compile(
    r"\b(api_key|token|password)\s*([=:])\s*([^\s,;]+)",
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
    jobs = list(db.execute(select(Job)).scalars().all())
    signal_payload = build_market_signal_payload(jobs=jobs, snapshot_date=target_date)

    try:
        report_payload = generate_market_report(signal_payload)
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


def _sanitize_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    message = DB_CREDENTIAL_URL_PATTERN.sub("[redacted]", message)
    message = OPENAI_KEY_PATTERN.sub("[redacted]", message)
    message = KEY_VALUE_SECRET_PATTERN.sub(_redact_key_value_secret, message)
    return message[:ERROR_MESSAGE_LIMIT]


def _redact_key_value_secret(match: re.Match) -> str:
    separator = match.group(2)
    if separator == ":":
        return f"{match.group(1)}: [redacted]"
    return f"{match.group(1)}=[redacted]"
