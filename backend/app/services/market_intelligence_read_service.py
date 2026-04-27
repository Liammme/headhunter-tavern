from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot


MARKET_INTELLIGENCE_VERSION = "market-intelligence-v1"


def load_latest_market_intelligence_for_home(db: Session) -> dict | None:
    snapshot = db.execute(
        select(MarketIntelligenceSnapshot)
        .where(MarketIntelligenceSnapshot.status.in_(("success", "fallback")))
        .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if snapshot is None:
        return None

    report = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
    headline = _non_empty_text(report.get("headline"))
    narrative = _non_empty_text(report.get("narrative"))
    if headline is None or narrative is None:
        return None

    return {
        "narrative": narrative,
        "headline": headline,
        "summary": _summary_from_report(report, fallback=headline),
        "analysis_version": MARKET_INTELLIGENCE_VERSION,
        "rule_version": MARKET_INTELLIGENCE_VERSION,
        "window_start": None,
        "window_end": snapshot.snapshot_date.isoformat(),
        "generated_at": snapshot.generated_at.replace(microsecond=0).isoformat(),
        "findings": _findings_from_report(report),
        "actions": _actions_from_report(report),
    }


def _summary_from_report(report: dict, *, fallback: str) -> str:
    primary_judgment = report.get("primary_judgment")
    if not isinstance(primary_judgment, dict):
        return fallback

    return _non_empty_text(primary_judgment.get("claim")) or fallback


def _findings_from_report(report: dict) -> list[str]:
    trend_cards = report.get("trend_cards")
    if not isinstance(trend_cards, list):
        return []

    for card in trend_cards:
        if not isinstance(card, dict):
            continue
        judgment = _non_empty_text(card.get("judgment"))
        if judgment is not None:
            return [judgment]
    return []


def _actions_from_report(report: dict) -> list[str]:
    watchlist = report.get("watchlist")
    if not isinstance(watchlist, list):
        return []

    for item in watchlist:
        action = _non_empty_text(item)
        if action is not None:
            return [action]
    return []


def _non_empty_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None
