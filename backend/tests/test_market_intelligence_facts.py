import json
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.crawlers.base import NormalizedJob
from app.models import Job, MarketIntelligenceFact, MarketIntelligenceSnapshot
from app.services.market_intelligence_baseline_service import generate_market_baseline_report
from app.services.market_intelligence_fact_extractor import extract_market_intelligence_fact
from app.services.market_intelligence_fact_service import backfill_market_intelligence_facts


FULL_DESCRIPTION = (
    "Build LLM serving, RAG systems, Kubernetes model deployment, "
    "and enterprise AI platform. Salary range: USD 120k-180k."
)


class StaticAdapter:
    source_name = "static"

    def __init__(self, jobs: list[NormalizedJob]):
        self._jobs = jobs

    def fetch(self) -> list[NormalizedJob]:
        return self._jobs


class FailingAdapter:
    source_name = "failing"

    def fetch(self) -> list[NormalizedJob]:
        raise RuntimeError("upstream blocked")


def _normalized_job(
    *,
    canonical_url: str = "https://jobs.example.com/opening/1?token=secret",
    title: str = "Senior AI Infrastructure Engineer",
    company: str = "OpenGradient",
    description: str = FULL_DESCRIPTION,
    posted_at: datetime | None = datetime(2026, 4, 20, 9, 0, 0),
    source_job_id: str | None = "remote-1",
) -> NormalizedJob:
    return NormalizedJob(
        source_job_id=source_job_id,
        canonical_url=canonical_url,
        title=title,
        company=company,
        description=description,
        posted_at=posted_at,
        raw_payload={"site": "static", "bounty": "high", "claim_url": "https://claims.example.com"},
    )


def test_extract_market_intelligence_fact_sanitizes_job_payload():
    extracted = extract_market_intelligence_fact(
        _normalized_job(),
        collected_at=datetime(2026, 4, 26, 12, 0, 0),
    )

    assert extracted is not None
    assert extracted.dedupe_key
    assert extracted.company == "OpenGradient"
    assert extracted.company_normalized == "opengradient"
    assert extracted.title == "Senior AI Infrastructure Engineer"
    assert extracted.job_function == "AI/算法"
    assert extracted.market_theme == "AI infra"
    assert extracted.seniority == "senior"
    assert extracted.salary_signal == "strong"
    assert "llm" in extracted.tech_keywords
    assert "enterprise" in extracted.business_keywords

    serialized = json.dumps(extracted.to_model_payload(), ensure_ascii=False, default=str)
    assert "canonical_url" not in serialized
    assert "jobs.example.com" not in serialized
    assert "claim_url" not in serialized
    assert "bounty" not in serialized.lower()
    assert FULL_DESCRIPTION not in serialized


def test_backfill_market_intelligence_facts_supports_dry_run_without_jobs_pollution(db_session):
    summary = backfill_market_intelligence_facts(
        db_session,
        days=180,
        dry_run=True,
        adapters=[StaticAdapter([_normalized_job()])],
        collected_at=datetime(2026, 4, 26, 12, 0, 0),
    )

    assert summary == {
        "days": 180,
        "dry_run": True,
        "fetched": 1,
        "eligible": 1,
        "inserted": 0,
        "skipped_duplicate": 0,
        "skipped_out_of_window": 0,
        "skipped_invalid": 0,
        "skipped_source_errors": 0,
        "source_errors": [],
    }
    assert db_session.execute(select(MarketIntelligenceFact)).scalars().all() == []
    assert db_session.execute(select(Job)).scalars().all() == []


def test_backfill_market_intelligence_facts_is_idempotent(db_session):
    adapter = StaticAdapter([_normalized_job()])
    kwargs = {
        "days": 180,
        "dry_run": False,
        "adapters": [adapter],
        "collected_at": datetime(2026, 4, 26, 12, 0, 0),
    }

    first = backfill_market_intelligence_facts(db_session, **kwargs)
    second = backfill_market_intelligence_facts(db_session, **kwargs)

    facts = db_session.execute(select(MarketIntelligenceFact)).scalars().all()
    assert first["inserted"] == 1
    assert first["skipped_duplicate"] == 0
    assert second["inserted"] == 0
    assert second["skipped_duplicate"] == 1
    assert len(facts) == 1
    assert db_session.execute(select(Job)).scalars().all() == []


def test_backfill_market_intelligence_facts_filters_by_days(db_session):
    collected_at = datetime(2026, 4, 26, 12, 0, 0)
    recent = _normalized_job(canonical_url="https://jobs.example.com/recent", posted_at=collected_at - timedelta(days=29))
    old = _normalized_job(canonical_url="https://jobs.example.com/old", posted_at=collected_at - timedelta(days=31))

    summary = backfill_market_intelligence_facts(
        db_session,
        days=30,
        dry_run=False,
        adapters=[StaticAdapter([recent, old])],
        collected_at=collected_at,
    )

    facts = db_session.execute(select(MarketIntelligenceFact)).scalars().all()
    assert summary["eligible"] == 1
    assert summary["skipped_out_of_window"] == 1
    assert len(facts) == 1
    assert facts[0].title == recent.title


def test_backfill_market_intelligence_facts_continues_when_source_fails(db_session):
    summary = backfill_market_intelligence_facts(
        db_session,
        days=180,
        dry_run=False,
        adapters=[FailingAdapter(), StaticAdapter([_normalized_job()])],
        collected_at=datetime(2026, 4, 26, 12, 0, 0),
    )

    facts = db_session.execute(select(MarketIntelligenceFact)).scalars().all()
    assert summary["fetched"] == 1
    assert summary["inserted"] == 1
    assert summary["skipped_source_errors"] == 1
    assert summary["source_errors"] == [
        {
            "source": "failing",
            "error": "RuntimeError: upstream blocked",
        }
    ]
    assert len(facts) == 1


def test_generate_market_baseline_report_uses_facts_without_sensitive_terms(db_session, monkeypatch):
    collected_at = datetime(2026, 4, 26, 12, 0, 0)
    backfill_market_intelligence_facts(
        db_session,
        days=180,
        dry_run=False,
        adapters=[
            StaticAdapter(
                [
                    _normalized_job(canonical_url="https://jobs.example.com/1", posted_at=collected_at - timedelta(days=5)),
                    _normalized_job(
                        canonical_url="https://jobs.example.com/2",
                        title="Data Platform Engineer",
                        posted_at=collected_at - timedelta(days=120),
                    ),
                ]
            )
        ],
        collected_at=collected_at,
    )

    def fake_generate_market_report(signal_payload):
        serialized_signal = json.dumps(signal_payload, ensure_ascii=False)
        assert "180d" in signal_payload["windows"]
        assert "canonical_url" not in serialized_signal
        assert "jobs.example.com" not in serialized_signal
        assert "bounty" not in serialized_signal.lower()
        assert "认领" not in serialized_signal
        assert FULL_DESCRIPTION not in serialized_signal
        return {"headline": "半年可见岗位基线", "narrative": "180天当前可见岗位基线。"}

    monkeypatch.setattr(
        "app.services.market_intelligence_baseline_service.generate_market_report",
        fake_generate_market_report,
    )

    result = generate_market_baseline_report(
        db_session,
        days=180,
        snapshot_date=date(2026, 4, 26),
        generated_at=datetime(2026, 4, 26, 14, 0, 0),
    )

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result == {"status": "success", "snapshot_id": snapshot.id}
    assert snapshot.window_days == 180
    assert snapshot.market_signal_payload["baseline_note"] == "当前可见岗位的历史基线，不代表完整真实半年历史。"
    assert snapshot.report_payload["headline"] == "半年可见岗位基线"
