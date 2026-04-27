from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services.market_intelligence_baseline_service import BASELINE_NOTE

WINDOWS = (7, 30, 90, 180)


def build_living_market_report_input(
    db: Session,
    *,
    mode: str,
    days: int = 180,
    snapshot_date: date,
    previous_snapshot: MarketIntelligenceSnapshot | None = None,
) -> dict:
    facts = _load_window_facts(db, snapshot_date=snapshot_date, days=days)
    samples = [_build_sample(fact, index=index) for index, fact in enumerate(_sorted_facts(facts), start=1)]
    market_windows = {f"{window}d": _build_window(facts=facts, snapshot_date=snapshot_date, days=window) for window in WINDOWS}
    previous_report = _previous_report_summary(previous_snapshot)
    new_facts = _new_facts(samples=samples, previous_snapshot=previous_snapshot)
    return {
        "report_task": {
            "report_id": "living-market-report",
            "language": "zh-CN",
            "target_length_words": [1500, 2500],
            "mode": "update" if mode == "update" else "initial",
            "snapshot_date": snapshot_date.isoformat(),
        },
        "previous_report": previous_report,
        "market_windows": market_windows,
        "deltas": {
            "7d_vs_30d": _delta(market_windows["7d"], market_windows["30d"]),
            "30d_vs_90d": _delta(market_windows["30d"], market_windows["90d"]),
            "90d_vs_180d": _delta(market_windows["90d"], market_windows["180d"]),
        },
        "new_facts": new_facts,
        "representative_samples": samples[:12],
        "allowed_evidence_terms": _allowed_terms(samples),
        "data_quality": _data_quality(facts),
    }


def _load_window_facts(db: Session, *, snapshot_date: date, days: int) -> list[MarketIntelligenceFact]:
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
    return [fact for fact in facts if 0 <= (snapshot_date - _time_basis(fact).date()).days < days]


def _build_window(*, facts: list[MarketIntelligenceFact], snapshot_date: date, days: int) -> dict:
    included = [fact for fact in facts if 0 <= (snapshot_date - _time_basis(fact).date()).days < days]
    return {
        "job_count": len(included),
        "theme_counts": dict(Counter(fact.market_theme for fact in included)),
        "function_counts": dict(Counter(fact.job_function for fact in included)),
        "seniority_counts": dict(Counter(fact.seniority for fact in included)),
        "salary_signal_counts": dict(Counter(fact.salary_signal for fact in included)),
    }


def _build_sample(fact: MarketIntelligenceFact, *, index: int) -> dict:
    return {
        "evidence_id": f"e{index}",
        "fact_id": fact.id,
        "created_at": fact.created_at.replace(microsecond=0).isoformat(),
        "company": fact.company,
        "title": fact.title,
        "posted_date": _time_basis(fact).date().isoformat(),
        "function": fact.job_function,
        "domain": fact.market_theme,
        "seniority": fact.seniority,
        "tech_keywords": fact.tech_keywords,
        "business_keywords": fact.business_keywords,
        "fact_summary": fact.fact_summary,
    }


def _previous_report_summary(snapshot: MarketIntelligenceSnapshot | None) -> dict | None:
    if snapshot is None:
        return None
    report = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
    living = report.get("living_report")
    if not isinstance(living, dict):
        return None
    claims = living.get("claims")
    active_claims = []
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict) and claim.get("status") != "retired":
                active_claims.append(
                    {
                        "claim_id": claim.get("claim_id"),
                        "claim": claim.get("claim"),
                        "confidence": claim.get("confidence"),
                    }
                )
    return {
        "version": living.get("version"),
        "summary": living.get("executive_summary"),
        "active_claims": active_claims,
        "fact_watermark": _fact_watermark_payload(snapshot),
    }


def _new_facts(*, samples: list[dict], previous_snapshot: MarketIntelligenceSnapshot | None) -> list[dict]:
    if previous_snapshot is None:
        return samples[:12]
    cutoff_at, cutoff_id = _fact_watermark(previous_snapshot)
    return [
        {
            "evidence_id": sample["evidence_id"],
            "title": sample["title"],
            "market_theme": sample["domain"],
            "function": sample["function"],
            "created_at": sample["created_at"],
        }
        for sample in samples
        if _is_after_watermark(sample, cutoff_at=cutoff_at, cutoff_id=cutoff_id)
    ][:12]


def _fact_watermark(snapshot: MarketIntelligenceSnapshot) -> tuple[datetime, int]:
    payload = snapshot.market_signal_payload if isinstance(snapshot.market_signal_payload, dict) else {}
    watermark = payload.get("fact_watermark")
    if isinstance(watermark, dict):
        created_at = watermark.get("created_at")
        fact_id = watermark.get("id")
        if isinstance(created_at, str) and isinstance(fact_id, int):
            return datetime.fromisoformat(created_at), fact_id
    return snapshot.generated_at, 0


def _fact_watermark_payload(snapshot: MarketIntelligenceSnapshot) -> dict:
    created_at, fact_id = _fact_watermark(snapshot)
    return {"created_at": created_at.replace(microsecond=0).isoformat(), "id": fact_id}


def _is_after_watermark(sample: dict, *, cutoff_at: datetime, cutoff_id: int) -> bool:
    created_at = datetime.fromisoformat(sample["created_at"])
    fact_id = sample.get("fact_id")
    if not isinstance(fact_id, int):
        fact_id = 0
    return (created_at, fact_id) > (cutoff_at, cutoff_id)


def _delta(short_window: dict, long_window: dict) -> dict:
    long_count = long_window.get("job_count") or 0
    short_count = short_window.get("job_count") or 0
    return {"job_count_ratio": round(short_count / long_count, 4) if long_count else 0}


def _data_quality(facts: list[MarketIntelligenceFact]) -> dict:
    return {
        "baseline_note": BASELINE_NOTE,
        "posted_at_fact_count": sum(1 for fact in facts if fact.posted_at is not None),
        "collected_at_fallback_count": sum(1 for fact in facts if fact.posted_at is None),
        "unknown_company_count": sum(1 for fact in facts if not fact.company),
        "sample_count": len(facts),
    }


def _allowed_terms(samples: list[dict]) -> list[str]:
    terms: list[str] = []
    for sample in samples:
        for field in ("evidence_id", "company", "title", "domain", "function", "seniority"):
            value = sample.get(field)
            if isinstance(value, str) and value.strip() and value not in terms:
                terms.append(value)
    return terms


def _sorted_facts(facts: list[MarketIntelligenceFact]) -> list[MarketIntelligenceFact]:
    return sorted(facts, key=lambda fact: (fact.created_at, _time_basis(fact), fact.id or 0), reverse=True)


def _time_basis(fact: MarketIntelligenceFact) -> datetime:
    return fact.posted_at or fact.collected_at
