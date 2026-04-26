from collections import Counter
from datetime import date, datetime, time

from app.models import Job
from app.services.market_theme_classifier import classify_market_theme

WINDOW_DAYS = (1, 7, 30, 90)
TECH_KEYWORDS = (
    "llm",
    "rag",
    "kubernetes",
    "serving",
    "inference",
    "platform",
    "retrieval",
    "workflow",
    "data pipeline",
    "warehouse",
    "analytics",
    "etl",
    "protocol",
    "node",
    "validator",
    "rpc",
    "chain",
    "sdk",
    "api",
)
BUSINESS_KEYWORDS = (
    "enterprise",
    "deployment",
    "implementation",
    "solution",
    "wallet",
    "payment",
    "card",
    "fiat",
    "settlement",
    "security",
    "audit",
    "threat",
    "vulnerability",
    "risk",
    "compliance",
    "kyc",
    "aml",
    "fraud",
    "trading",
    "market making",
    "exchange",
    "liquidity",
)


def build_market_signal_payload(*, jobs: list[Job], snapshot_date: date) -> dict:
    windows = {
        f"{days}d": _build_window(jobs=jobs, snapshot_date=snapshot_date, days=days)
        for days in WINDOW_DAYS
    }
    return {
        "snapshot_date": snapshot_date.isoformat(),
        "windows": windows,
        "representative_samples": [
            _build_sample(job) for job in _sorted_jobs(jobs)[:12]
        ],
        "historical_comparison": {
            "continuing_signals": [],
            "reversals": [],
            "emerging_signals": [],
        },
    }


def _build_window(*, jobs: list[Job], snapshot_date: date, days: int) -> dict:
    included = [job for job in jobs if _days_ago(job, snapshot_date) < days]
    theme_counts = Counter(_domain(job) for job in included)
    function_counts = Counter(_function(job) for job in included)
    return {
        "job_count": len(included),
        "theme_counts": dict(theme_counts),
        "function_counts": dict(function_counts),
    }


def _build_sample(job: Job) -> dict:
    tech_keywords = _extract_keywords(job.description or "", TECH_KEYWORDS)
    business_keywords = _extract_keywords(job.description or "", BUSINESS_KEYWORDS)
    domain = _domain(job)
    return {
        "company": job.company,
        "title": job.title,
        "posted_date": _posted_date(job),
        "function": _function(job),
        "domain": domain,
        "seniority": _seniority(job.title),
        "tech_keywords": tech_keywords,
        "business_keywords": business_keywords,
        "jd_summary": _summary(domain, tech_keywords, business_keywords),
        "signal_reason": _signal_reason(domain, tech_keywords, business_keywords),
    }


def _sorted_jobs(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: _time_basis(job), reverse=True)


def _days_ago(job: Job, snapshot_date: date) -> int:
    return (snapshot_date - _time_basis(job).date()).days


def _time_basis(job: Job) -> datetime:
    value = job.collected_at or job.posted_at
    if value is None:
        return datetime.combine(date.min, time.min)
    return value


def _domain(job: Job) -> str:
    return classify_market_theme(job.title or "", job.description or "")


def _function(job: Job) -> str:
    return job.job_category or "其他"


def _posted_date(job: Job) -> str | None:
    value = job.posted_at or job.collected_at
    return value.date().isoformat() if value else None


def _seniority(title: str) -> str:
    lowered = title.lower()
    if any(keyword in lowered for keyword in ("principal", "staff", "lead")):
        return "Lead"
    if "senior" in lowered or "sr." in lowered:
        return "Senior"
    return "Mid"


def _extract_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _summary(
    domain: str, tech_keywords: list[str], business_keywords: list[str]
) -> str:
    keywords = [*tech_keywords, *business_keywords][:5]
    if keywords:
        return f"{domain}: {', '.join(keywords)}"
    return domain


def _signal_reason(
    domain: str, tech_keywords: list[str], business_keywords: list[str]
) -> str:
    keywords = [*tech_keywords, *business_keywords]
    if keywords:
        return f"Matched {domain} keywords: {', '.join(keywords[:3])}"
    return f"Classified as {domain}"
