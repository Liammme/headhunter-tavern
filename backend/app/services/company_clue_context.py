from collections import Counter
from datetime import date, timedelta
import re

from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import BountyEstimate
from app.services.feed_snapshot import WINDOW_DAYS
from app.services.job_facts import StandardizedJobInput, build_v2_score_input, extract_job_facts
from app.services.scoring import score_job_v2


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def load_company_jobs_for_clue(db: Session, *, company: str, today: date) -> list[Job]:
    window_start = today - timedelta(days=WINDOW_DAYS - 1)
    jobs = (
        db.query(Job)
        .filter(Job.company == company)
        .order_by(Job.collected_at.desc(), Job.id.desc())
        .all()
    )
    return [job for job in jobs if _job_reference_date(job) >= window_start]


def build_company_clue_context(*, company: str, jobs: list[Job], today: date) -> dict:
    evidence_cards = [_build_evidence_card(job) for job in jobs]
    categories = Counter(card["category"] for card in evidence_cards)
    domains = Counter(card["domain_tag"] for card in evidence_cards)
    return {
        "company": company,
        "window": {
            "window_days": WINDOW_DAYS,
            "window_start": (today - timedelta(days=WINDOW_DAYS - 1)).isoformat(),
            "window_end": today.isoformat(),
        },
        "summary": {
            "total_jobs": len(jobs),
            "high_bounty_jobs": sum(1 for card in evidence_cards if card["bounty_grade"] == "high"),
            "urgent_jobs": sum(1 for card in evidence_cards if card["urgent"]),
            "critical_jobs": sum(1 for card in evidence_cards if card["critical"]),
            "top_categories": [name for name, _count in categories.most_common(3)],
            "top_domains": [name for name, _count in domains.most_common(3)],
            "estimated_bounty": _collect_estimated_bounty(jobs),
        },
        "role_clusters": _build_role_clusters(evidence_cards)[:3],
        "evidence_cards": evidence_cards[:5],
        "entry_points": _collect_entry_points(jobs),
    }


def _build_evidence_card(job: Job) -> dict:
    facts = extract_job_facts(
        StandardizedJobInput(
            canonical_url=job.canonical_url,
            source_name=job.source_name,
            title=job.title,
            company=job.company,
            company_normalized=job.company_normalized,
            description=job.description,
            posted_at=job.posted_at,
            collected_at=job.collected_at,
        ),
        now=job.collected_at,
    )
    score_result = score_job_v2(build_v2_score_input(facts))
    return {
        "title": job.title,
        "posted_at": _job_reference_datetime(job).replace(microsecond=0).isoformat(),
        "bounty_grade": job.bounty_grade,
        "category": facts.category,
        "domain_tag": facts.domain_tag,
        "seniority": facts.seniority,
        "urgent": facts.urgent,
        "critical": facts.critical,
        "hard_to_fill": facts.hard_to_fill,
        "business_criticality": facts.business_criticality,
        "time_pressure_signals": list(facts.time_pressure_signals),
        "anomaly_signals": list(facts.anomaly_signals),
        "v2_reasons": list(score_result.reasons),
        "rule_hits": [hit.code for hit in score_result.rule_hits],
        "entry_points": {
            "job_post": job.canonical_url,
            "company_url": _read_signal_tag(job, "company_url"),
            "hiring_page": _read_signal_tag(job, "hiring_page_url", "apply_url"),
            "email": _extract_email(job),
        },
        "evidence_snippets": _extract_evidence_snippets(job.description or ""),
    }


def _build_role_clusters(evidence_cards: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for card in evidence_cards:
        key = (card["category"], card["seniority"])
        cluster = grouped.setdefault(
            key,
            {
                "category": card["category"],
                "seniority": card["seniority"],
                "job_count": 0,
                "titles": [],
                "critical_jobs": 0,
                "urgent_jobs": 0,
            },
        )
        cluster["job_count"] += 1
        cluster["critical_jobs"] += 1 if card["critical"] else 0
        cluster["urgent_jobs"] += 1 if card["urgent"] else 0
        if card["title"] not in cluster["titles"]:
            cluster["titles"].append(card["title"])
    return sorted(grouped.values(), key=lambda item: (-item["job_count"], -item["critical_jobs"], item["category"]))


def _extract_evidence_snippets(description: str) -> list[str]:
    normalized = " ".join(description.split())
    candidates = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", normalized) if chunk.strip()]
    prioritized = [
        chunk
        for chunk in candidates
        if any(
            token in chunk.lower()
            for token in ("urgent", "hiring", "architect", "lead", "principal", "manager", "platform", "remote")
        )
    ]
    selected = prioritized[:2] or candidates[:1]
    return [item[:180] for item in selected]


def _collect_estimated_bounty(jobs: list[Job]) -> dict | None:
    for job in jobs:
        estimate = BountyEstimate.from_signal_tags(job.signal_tags if isinstance(job.signal_tags, dict) else None)
        if estimate is not None:
            return {"amount": estimate.amount, "label": estimate.label}
    return None


def _collect_entry_points(jobs: list[Job]) -> dict:
    company_urls = _dedupe_non_empty(_read_signal_tag(job, "company_url") for job in jobs)
    hiring_pages = _dedupe_non_empty(_read_signal_tag(job, "hiring_page_url", "apply_url") for job in jobs)
    job_posts = _dedupe_non_empty(job.canonical_url for job in jobs)
    emails = _dedupe_non_empty(_extract_email(job) for job in jobs)
    return {
        "company_urls": company_urls[:3],
        "hiring_pages": hiring_pages[:3],
        "job_posts": job_posts[:5],
        "emails": emails[:3],
    }


def _read_signal_tag(job: Job, *keys: str) -> str | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    for key in keys:
        value = signal_tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_email(job: Job) -> str | None:
    match = EMAIL_PATTERN.search(job.description or "")
    if match is None:
        return None
    return match.group(0)


def _dedupe_non_empty(values) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if not value or value in deduped:
            continue
        deduped.append(value)
    return deduped


def _job_reference_datetime(job: Job):
    return job.posted_at or job.collected_at


def _job_reference_date(job: Job) -> date:
    return _job_reference_datetime(job).date()
