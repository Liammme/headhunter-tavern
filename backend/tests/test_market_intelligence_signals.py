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
    posted_days_ago: int | None = None,
    collected_days_ago: int | None = None,
    missing_timestamps: bool = False,
    job_category: str = "技术",
    domain_tag: str = "AI",
    source_name: str = "demo-board",
) -> Job:
    snapshot_date = date(2026, 4, 26)
    base_time = datetime.combine(snapshot_date, datetime.min.time())
    posted_at = base_time - timedelta(
        days=days_ago if posted_days_ago is None else posted_days_ago
    )
    collected_at = base_time - timedelta(
        days=days_ago if collected_days_ago is None else collected_days_ago
    )
    if missing_timestamps:
        posted_at = None
        collected_at = None
    return Job(
        id=job_id,
        canonical_url=f"https://jobs.example.com/{job_id}",
        source_name=source_name,
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=posted_at,
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


def test_build_market_signal_payload_does_not_treat_aijobs_source_as_company():
    payload = build_market_signal_payload(
        jobs=[
            build_job(
                title="Networking Software Expert",
                company="Aijobs",
                job_id=1,
                source_name="aijobsnet",
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    sample = payload["representative_samples"][0]
    assert sample["company"] is None

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "Aijobs" not in serialized


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


def test_build_market_signal_payload_prefers_posted_at_over_collected_at():
    payload = build_market_signal_payload(
        jobs=[
            build_job(
                job_id=1,
                title="Old AI Engineer",
                posted_days_ago=120,
                collected_days_ago=0,
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert payload["windows"]["1d"]["job_count"] == 0
    assert payload["windows"]["90d"]["job_count"] == 0
    assert payload["representative_samples"] == []


def test_build_market_signal_payload_excludes_jobs_with_missing_timestamps_from_samples():
    payload = build_market_signal_payload(
        jobs=[
            build_job(
                job_id=1,
                title="Undated AI Engineer",
                missing_timestamps=True,
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert payload["windows"]["90d"]["job_count"] == 0
    assert payload["representative_samples"] == []


def test_build_market_signal_payload_excludes_future_dated_jobs():
    payload = build_market_signal_payload(
        jobs=[
            build_job(
                job_id=1,
                title="Future AI Engineer",
                days_ago=-1,
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert payload["windows"]["1d"]["job_count"] == 0
    assert payload["windows"]["7d"]["job_count"] == 0
    assert payload["windows"]["30d"]["job_count"] == 0
    assert payload["windows"]["90d"]["job_count"] == 0
    assert payload["representative_samples"] == []


def test_build_market_signal_payload_excludes_exact_window_boundaries():
    payload = build_market_signal_payload(
        jobs=[
            build_job(job_id=1, title="One Day Boundary", days_ago=1),
            build_job(job_id=2, title="Seven Day Boundary", days_ago=7),
            build_job(job_id=3, title="Thirty Day Boundary", days_ago=30),
            build_job(job_id=4, title="Ninety Day Boundary", days_ago=90),
        ],
        snapshot_date=date(2026, 4, 26),
    )

    assert payload["windows"]["1d"]["job_count"] == 0
    assert payload["windows"]["7d"]["job_count"] == 1
    assert payload["windows"]["30d"]["job_count"] == 2
    assert payload["windows"]["90d"]["job_count"] == 3
    assert len(payload["representative_samples"]) == 3


def test_classify_market_theme_uses_first_matching_theme_keyword():
    assert (
        classify_market_theme(
            "AI Infrastructure Engineer",
            "Own LLM inference and Kubernetes serving platform.",
        )
        == "AI infra"
    )
