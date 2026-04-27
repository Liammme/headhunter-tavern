from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services.market_intelligence_fact_service import SUPPORTED_BACKFILL_DAYS
from app.services.market_intelligence_report import (
    MarketIntelligenceReportError,
    build_rule_market_report,
    generate_market_report,
)

BASELINE_NOTE = "当前可见岗位的历史基线，不代表完整真实半年历史。"


def generate_market_baseline_report(
    db: Session,
    *,
    days: int,
    snapshot_date: date | None = None,
    generated_at: datetime | None = None,
) -> dict:
    if days not in SUPPORTED_BACKFILL_DAYS:
        raise ValueError("days must be one of 30, 90, or 180")

    generated_at = (generated_at or datetime.now()).replace(microsecond=0)
    snapshot_date = snapshot_date or generated_at.date()
    facts = _load_window_facts(db, snapshot_date=snapshot_date, days=days)
    signal_payload = build_market_baseline_signal_payload(
        facts=facts,
        snapshot_date=snapshot_date,
        days=days,
    )
    if db.in_transaction():
        db.commit()

    try:
        report_payload = generate_market_report(signal_payload)
        status = "success"
        error_message = None
    except MarketIntelligenceReportError as exc:
        report_payload = build_rule_market_report(signal_payload)
        status = "fallback"
        error_message = str(exc)[:500]
    except Exception as exc:
        snapshot = MarketIntelligenceSnapshot(
            snapshot_date=snapshot_date,
            generated_at=generated_at,
            window_days=days,
            market_signal_payload=signal_payload,
            report_payload={},
            model_name=None,
            status="failed",
            error_message=str(exc)[:500],
        )
        db.add(snapshot)
        db.commit()
        return {"status": "failed", "error": snapshot.error_message}

    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=snapshot_date,
        generated_at=generated_at,
        window_days=days,
        market_signal_payload=signal_payload,
        report_payload=report_payload,
        model_name=None,
        status=status,
        error_message=error_message,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": status, "snapshot_id": snapshot.id}


def build_market_baseline_signal_payload(
    *,
    facts: list[MarketIntelligenceFact],
    snapshot_date: date,
    days: int,
) -> dict:
    windows = {
        f"{window_days}d": _build_window(facts=facts, snapshot_date=snapshot_date, days=window_days)
        for window_days in _window_days(days)
    }
    return {
        "snapshot_date": snapshot_date.isoformat(),
        "baseline_note": BASELINE_NOTE,
        "windows": windows,
        "representative_samples": [_build_sample(fact) for fact in _sorted_facts(facts)[:12]],
        "historical_comparison": {
            "continuing_signals": [],
            "reversals": [],
            "emerging_signals": [],
        },
    }


def _load_window_facts(
    db: Session,
    *,
    snapshot_date: date,
    days: int,
) -> list[MarketIntelligenceFact]:
    cutoff = datetime.combine(snapshot_date - timedelta(days=days - 1), datetime.min.time())
    facts = list(
        db.execute(
            select(MarketIntelligenceFact).where(
                or_(
                    MarketIntelligenceFact.posted_at >= cutoff,
                    MarketIntelligenceFact.posted_at.is_(None)
                    & (MarketIntelligenceFact.collected_at >= cutoff),
                )
            )
        )
        .scalars()
        .all()
    )
    return _window_facts(facts=facts, snapshot_date=snapshot_date, days=days)


def _window_days(days: int) -> tuple[int, ...]:
    if days == 30:
        return (30,)
    if days == 90:
        return (30, 90)
    return (30, 90, 180)


def _build_window(*, facts: list[MarketIntelligenceFact], snapshot_date: date, days: int) -> dict:
    included = _window_facts(facts=facts, snapshot_date=snapshot_date, days=days)
    theme_counts = Counter(fact.market_theme for fact in included)
    function_counts = Counter(fact.job_function for fact in included)
    seniority_counts = Counter(fact.seniority for fact in included)
    salary_signal_counts = Counter(fact.salary_signal for fact in included)
    return {
        "job_count": len(included),
        "theme_counts": dict(theme_counts),
        "function_counts": dict(function_counts),
        "seniority_counts": dict(seniority_counts),
        "salary_signal_counts": dict(salary_signal_counts),
    }


def _window_facts(*, facts: list[MarketIntelligenceFact], snapshot_date: date, days: int) -> list[MarketIntelligenceFact]:
    included = []
    for fact in facts:
        days_ago = (snapshot_date - _time_basis(fact).date()).days
        if 0 <= days_ago < days:
            included.append(fact)
    return included


def _build_sample(fact: MarketIntelligenceFact) -> dict:
    return {
        "company": fact.company,
        "title": fact.title,
        "posted_date": _time_basis(fact).date().isoformat(),
        "function": fact.job_function,
        "domain": fact.market_theme,
        "seniority": fact.seniority,
        "tech_keywords": fact.tech_keywords,
        "business_keywords": fact.business_keywords,
        "jd_summary": fact.fact_summary,
    }


def _sorted_facts(facts: list[MarketIntelligenceFact]) -> list[MarketIntelligenceFact]:
    return sorted(facts, key=_time_basis, reverse=True)


def _time_basis(fact: MarketIntelligenceFact) -> datetime:
    return fact.posted_at or fact.collected_at
