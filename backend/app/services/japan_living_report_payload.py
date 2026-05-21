from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services.japan_market_profile import JAPAN_RECRUITING_MARKET_PROFILE
from app.services.market_intelligence_living_payload import build_living_market_report_input
from app.services.region import JAPAN_REGION

WINDOWS = (7, 30, 90, 180)
PROFILE_FIELDS = (
    ("source_family", "source_mix"),
    ("location_signal", "location_counts"),
    ("remote_policy", "remote_policy_counts"),
    ("employment_type", "employment_type_counts"),
    ("experience_level", "experience_counts"),
    ("language_requirement", "language_counts"),
    ("salary_disclosure", "salary_disclosure_counts"),
    ("salary_type", "salary_type_counts"),
    ("industry_hint", "industry_hint_counts"),
)


def build_japan_living_market_report_input(
    db: Session,
    *,
    mode: str,
    days: int = 180,
    snapshot_date: date,
    previous_snapshot: MarketIntelligenceSnapshot | None = None,
) -> dict:
    payload = build_living_market_report_input(
        db,
        mode=mode,
        days=days,
        snapshot_date=snapshot_date,
        previous_snapshot=previous_snapshot,
        region=JAPAN_REGION,
    )
    facts = _load_window_facts(db, snapshot_date=snapshot_date, days=days)
    payload["report_profile"] = JAPAN_RECRUITING_MARKET_PROFILE
    payload["japan_recruiting_profile"] = _build_recruiting_profile(facts=facts, snapshot_date=snapshot_date)
    return payload


def _load_window_facts(db: Session, *, snapshot_date: date, days: int) -> list[MarketIntelligenceFact]:
    cutoff = datetime.combine(snapshot_date - timedelta(days=days - 1), datetime.min.time())
    facts = list(
        db.execute(
            select(MarketIntelligenceFact).where(
                MarketIntelligenceFact.region == JAPAN_REGION,
                or_(
                    MarketIntelligenceFact.posted_at >= cutoff,
                    MarketIntelligenceFact.posted_at.is_(None)
                    & (MarketIntelligenceFact.collected_at >= cutoff),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [fact for fact in facts if 0 <= (snapshot_date - _time_basis(fact).date()).days < days]


def _build_recruiting_profile(*, facts: list[MarketIntelligenceFact], snapshot_date: date) -> dict:
    return {
        "profile": JAPAN_RECRUITING_MARKET_PROFILE,
        "primary_dimensions": [
            "function_counts",
            "experience_counts",
            "language_counts",
            "location_counts",
            "remote_policy_counts",
            "employment_type_counts",
            "salary_disclosure_counts",
            "source_mix",
        ],
        "industry_hints_are_secondary": True,
        "windows": {f"{window}d": _build_window(facts=facts, snapshot_date=snapshot_date, days=window) for window in WINDOWS},
    }


def _build_window(*, facts: list[MarketIntelligenceFact], snapshot_date: date, days: int) -> dict:
    included = [fact for fact in facts if 0 <= (snapshot_date - _time_basis(fact).date()).days < days]
    window = {
        "job_count": len(included),
        "function_counts": dict(Counter(fact.job_function for fact in included)),
        "seniority_counts": dict(Counter(fact.seniority for fact in included)),
    }
    for profile_key, output_key in PROFILE_FIELDS:
        window[output_key] = dict(Counter(_profile_value(fact, profile_key) for fact in included))
    return window


def _profile_value(fact: MarketIntelligenceFact, key: str) -> str:
    profile = fact.profile_payload if isinstance(fact.profile_payload, dict) else {}
    value = profile.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return "unknown"


def _time_basis(fact: MarketIntelligenceFact) -> datetime:
    return fact.posted_at or fact.collected_at
