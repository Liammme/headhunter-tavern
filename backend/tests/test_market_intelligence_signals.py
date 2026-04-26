import json
from datetime import date, datetime, timedelta

from app.models import Job
from app.services.market_theme_classifier import classify_market_theme
from app.services.market_signal_builder import build_market_signal_payload


FULL_DESCRIPTION = (
    "Build LLM serving, RAG systems, Kubernetes model deployment, "
    "and enterprise AI platform."
)


def build_job(
    *,
    job_id: int = 1,
    title: str,
    company: str = "OpenGradient",
    description: str = FULL_DESCRIPTION,
    days_ago: int = 0,
    job_category: str = "技术",
    domain_tag: str = "AI",
) -> Job:
    snapshot_date = date(2026, 4, 26)
    collected_at = datetime.combine(snapshot_date, datetime.min.time()) - timedelta(
        days=days_ago
    )
    return Job(
        id=job_id,
        canonical_url=f"https://jobs.example.com/{job_id}",
        source_name="demo-board",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=collected_at,
        collected_at=collected_at,
        job_category=job_category,
        domain_tag=domain_tag,
        bounty_grade="high",
        signal_tags={
            "claimed_names": ["Alice"],
            "bd_entry": "email",
            "salary": "100K-200K",
        },
    )


def test_build_market_signal_payload_sanitizes_sensitive_job_fields():
    payload = build_market_signal_payload(
        jobs=[
            build_job(
                title="AI Infrastructure Engineer",
                company="OpenGradient",
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert "1d" in payload["windows"]
    assert "30d" in payload["windows"]
    assert "90d" in payload["windows"]
    assert payload["representative_samples"][0]["company"] == "OpenGradient"
    assert payload["representative_samples"][0]["domain"] == "AI infra"

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "canonical_url" not in serialized
    assert "source_name" not in serialized
    assert "bounty" not in serialized
    assert "claimed" not in serialized
    assert "bd_entry" not in serialized
    assert FULL_DESCRIPTION not in serialized


def test_build_market_signal_payload_counts_jobs_by_windows():
    payload = build_market_signal_payload(
        jobs=[
            build_job(job_id=1, title="AI Engineer", days_ago=0),
            build_job(job_id=2, title="RAG Engineer", days_ago=6),
            build_job(job_id=3, title="Data Platform Engineer", days_ago=29),
            build_job(job_id=4, title="Security Engineer", days_ago=60),
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert payload["windows"]["1d"]["job_count"] == 1
    assert payload["windows"]["7d"]["job_count"] == 2
    assert payload["windows"]["30d"]["job_count"] == 3
    assert payload["windows"]["90d"]["job_count"] == 4


def test_classify_market_theme_uses_first_matching_theme_keyword():
    assert (
        classify_market_theme(
            "AI Infrastructure Engineer",
            "Own LLM inference and Kubernetes serving platform.",
        )
        == "AI infra"
    )
