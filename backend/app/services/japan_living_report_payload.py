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
    samples = [_build_sample(fact) for fact in _sorted_facts(facts)]
    payload["report_profile"] = JAPAN_RECRUITING_MARKET_PROFILE
    payload["japan_recruiting_profile"] = _build_recruiting_profile(facts=facts, snapshot_date=snapshot_date)
    payload["legacy_window_counts"] = _legacy_window_counts(payload)
    payload.pop("market_windows", None)
    payload.pop("deltas", None)
    payload["new_facts"] = _new_facts(samples=samples, previous_snapshot=previous_snapshot)
    payload["new_fact_count"] = len(payload["new_facts"])
    payload["representative_samples"] = samples[:12]
    payload["allowed_evidence_terms"] = _allowed_terms(payload["representative_samples"])
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


def _build_sample(fact: MarketIntelligenceFact) -> dict:
    profile = fact.profile_payload if isinstance(fact.profile_payload, dict) else {}
    return {
        "evidence_id": f"fact-{fact.id}" if fact.id is not None else f"fact-{fact.dedupe_key[:12]}",
        "fact_id": fact.id,
        "created_at": fact.created_at.replace(microsecond=0).isoformat(),
        "company": fact.company,
        "title": fact.title,
        "posted_date": _time_basis(fact).date().isoformat(),
        "function": fact.job_function,
        "seniority": fact.seniority,
        "tech_keywords": fact.tech_keywords,
        "business_keywords": fact.business_keywords,
        "profile": profile,
    }


def _profile_value(fact: MarketIntelligenceFact, key: str) -> str:
    profile = fact.profile_payload if isinstance(fact.profile_payload, dict) else {}
    value = profile.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return "unknown"


def _legacy_window_counts(payload: dict) -> dict:
    windows = payload.get("market_windows")
    if not isinstance(windows, dict):
        return {}
    result = {}
    for window, value in windows.items():
        if isinstance(value, dict):
            result[window] = {"job_count": value.get("job_count") or 0}
    return result


def _new_facts(*, samples: list[dict], previous_snapshot: MarketIntelligenceSnapshot | None) -> list[dict]:
    if previous_snapshot is None:
        return [_new_fact_payload(sample) for sample in samples]
    cutoff_at, cutoff_id = _fact_watermark(previous_snapshot)
    return [
        _new_fact_payload(sample)
        for sample in samples
        if _is_after_watermark(sample, cutoff_at=cutoff_at, cutoff_id=cutoff_id)
    ]


def _new_fact_payload(sample: dict) -> dict:
    return {
        "evidence_id": sample.get("evidence_id"),
        "title": sample.get("title"),
        "function": sample.get("function"),
        "created_at": sample.get("created_at"),
        "profile": sample.get("profile") if isinstance(sample.get("profile"), dict) else {},
    }


def _fact_watermark(snapshot: MarketIntelligenceSnapshot) -> tuple[datetime, int]:
    payload = snapshot.market_signal_payload if isinstance(snapshot.market_signal_payload, dict) else {}
    watermark = payload.get("fact_watermark")
    if isinstance(watermark, dict):
        created_at = watermark.get("created_at")
        fact_id = watermark.get("id")
        if isinstance(created_at, str) and isinstance(fact_id, int):
            return datetime.fromisoformat(created_at), fact_id
    return snapshot.generated_at, 0


def _is_after_watermark(sample: dict, *, cutoff_at: datetime, cutoff_id: int) -> bool:
    created_at = sample.get("created_at")
    fact_id = sample.get("fact_id")
    if not isinstance(created_at, str):
        return False
    if not isinstance(fact_id, int):
        fact_id = 0
    return (datetime.fromisoformat(created_at), fact_id) > (cutoff_at, cutoff_id)


def _allowed_terms(samples: list[dict]) -> list[str]:
    terms: list[str] = []
    for sample in samples:
        for field in ("evidence_id", "company", "title", "function", "seniority"):
            value = sample.get(field)
            if isinstance(value, str) and value.strip() and value not in terms:
                terms.append(value)
    return terms


def _sorted_facts(facts: list[MarketIntelligenceFact]) -> list[MarketIntelligenceFact]:
    return sorted(facts, key=lambda fact: (fact.created_at, _time_basis(fact), fact.id or 0), reverse=True)


def _time_basis(fact: MarketIntelligenceFact) -> datetime:
    return fact.posted_at or fact.collected_at
