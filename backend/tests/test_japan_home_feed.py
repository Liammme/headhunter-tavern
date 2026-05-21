from datetime import date, datetime

from app.models import Job, JobClaim, MarketIntelligenceSnapshot
from app.services.regional_home_feed import build_region_home_payload
from app.services.region import GLOBAL_REGION, JAPAN_REGION


def _add_job(
    db_session,
    *,
    region: str,
    canonical_url: str,
    title: str,
    company: str,
    signal_tags: dict | None = None,
) -> Job:
    job = Job(
        canonical_url=canonical_url,
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower().replace(" ", "-"),
        description="Build market signal products.",
        posted_at=datetime.now().replace(microsecond=0),
        collected_at=datetime.now().replace(microsecond=0),
        bounty_grade="high",
        signal_tags=signal_tags or {"display_tags": ["Japan" if region == JAPAN_REGION else "Global"]},
        region=region,
    )
    db_session.add(job)
    db_session.commit()
    return job


def test_japan_home_payload_only_returns_japan_jobs_without_jdtrust_or_verification_tags(db_session):
    _add_job(
        db_session,
        region=GLOBAL_REGION,
        canonical_url="https://jobs.example.com/global-role",
        title="Global Engineer",
        company="Global Co",
    )
    _add_job(
        db_session,
        region=JAPAN_REGION,
        canonical_url="https://jobs.example.jp/japan-role",
        title="Japan Engineer",
        company="Tokyo Signal",
    )

    payload = build_region_home_payload(db_session, JAPAN_REGION)

    companies = payload["days"][0]["companies"]
    assert [company["company"] for company in companies] == ["Tokyo Signal"]
    assert companies[0]["jd_trust"] is None
    assert companies[0]["jobs"][0]["verification_tags"] == []


def test_japan_home_payload_does_not_expose_historical_claims(db_session):
    job = _add_job(
        db_session,
        region=JAPAN_REGION,
        canonical_url="https://jobs.example.jp/japan-role",
        title="Japan Engineer",
        company="Tokyo Signal",
    )
    db_session.add(JobClaim(job_id=job.id, claimer_name="Legacy Claimer"))
    db_session.commit()

    payload = build_region_home_payload(db_session, JAPAN_REGION)

    company = payload["days"][0]["companies"][0]
    assert company["claimed_names"] == []
    assert company["claimed_by"] is None
    assert company["claim_status"] is None


def test_japan_home_payload_does_not_expose_estimated_bounty_fields(db_session):
    _add_job(
        db_session,
        region=JAPAN_REGION,
        canonical_url="https://jobs.example.jp/japan-role",
        title="Japan Engineer",
        company="Tokyo Signal",
        signal_tags={
            "display_tags": ["Japan"],
            "estimated_bounty_amount": 12600,
            "estimated_bounty_label": "¥7,200-¥18,000",
            "estimated_bounty_min": 7200,
            "estimated_bounty_max": 18000,
            "estimated_bounty_rate_pct": 10,
            "estimated_bounty_rule_version": "bounty-rule-v2",
            "estimated_bounty_confidence": "high",
        },
    )

    payload = build_region_home_payload(db_session, JAPAN_REGION)

    company = payload["days"][0]["companies"][0]
    assert company["estimated_bounty_amount"] is None
    assert company["estimated_bounty_label"] is None


def test_japan_home_payload_does_not_500_when_empty(db_session):
    payload = build_region_home_payload(db_session, JAPAN_REGION)

    assert payload["days"] == []
    assert payload["intelligence"]["headline"]


def test_japan_home_prefers_japan_market_intelligence(db_session):
    _add_job(
        db_session,
        region=JAPAN_REGION,
        canonical_url="https://jobs.example.jp/japan-role",
        title="Japan Engineer",
        company="Tokyo Signal",
    )
    db_session.add(
        MarketIntelligenceSnapshot(
            region=JAPAN_REGION,
            snapshot_date=date(2026, 5, 1),
            generated_at=datetime(2026, 5, 1, 10, 0, 0),
            window_days=90,
            market_signal_payload={"region": JAPAN_REGION},
            report_payload={
                "region": JAPAN_REGION,
                "headline": "Japan report",
                "narrative": "Japan narrative",
                "primary_judgment": {"claim": "Japan summary"},
                "trend_cards": [],
                "watchlist": [],
            },
            model_name=None,
            status="success",
            error_message=None,
        )
    )
    db_session.commit()

    payload = build_region_home_payload(db_session, JAPAN_REGION)

    assert payload["intelligence"]["headline"] == "Japan report"
