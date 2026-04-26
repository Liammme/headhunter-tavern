from dataclasses import dataclass
from datetime import datetime
import re

from app.crawlers.base import NormalizedJob
from app.services.scoring import JobScoreInput, JobScoreV2Input

LONG_RUNNING_DAYS = 7
CURRENCY_TO_CNY_RATE = {
    "cny": 1.0,
    "rmb": 1.0,
    "usd": 7.2,
    "cad": 5.2,
    "eur": 7.8,
    "gbp": 9.1,
    "inr": 0.086,
    "thb": 0.20,
    "czk": 0.31,
    "brl": 1.3,
}


@dataclass(frozen=True)
class StandardizedJobInput:
    canonical_url: str
    source_name: str
    title: str
    company: str
    company_normalized: str
    description: str
    posted_at: datetime | None
    collected_at: datetime


@dataclass(frozen=True)
class JobFacts:
    title: str
    category: str
    domain_tag: str
    seniority: str
    urgent: bool
    critical: bool
    bd_entry: bool
    hard_to_fill: bool
    role_complexity: str
    business_criticality: str
    anomaly_signals: tuple[str, ...]
    compensation_signal: str
    company_signal: str
    time_pressure_signals: tuple[str, ...]
    annual_salary_range: tuple[int, int] | None = None


def standardize_job_input(job: NormalizedJob, *, now: datetime | None = None) -> StandardizedJobInput:
    collected_at = (now or datetime.now()).replace(microsecond=0)
    title = (job.title or "").strip()
    description = (job.description or "").strip()[:4000]
    company = (job.company or "").strip() or derive_company_name(job.canonical_url)
    source_name = (
        getattr(job, "source_name", None)
        or (job.raw_payload.get("site") if isinstance(job.raw_payload, dict) else "")
        or "crawler"
    )
    return StandardizedJobInput(
        canonical_url=job.canonical_url,
        source_name=source_name,
        title=title,
        company=company,
        company_normalized=normalize_company_name(company),
        description=description,
        posted_at=job.posted_at,
        collected_at=collected_at,
    )


def extract_job_facts(job: StandardizedJobInput, *, now: datetime | None = None) -> JobFacts:
    now = (now or datetime.now()).replace(microsecond=0)
    text = f"{job.title} {job.description}".lower()
    title_text = job.title.lower()
    category = classify_job_category(job.title, job.description)
    domain_tag = classify_domain_tag(job.title, job.description, job.canonical_url)
    seniority = classify_seniority(title_text)
    urgent = has_any_keyword(text, ("urgent", "asap", "immediately", "hiring fast"))
    critical = seniority in {"staff", "principal", "lead", "head", "director", "vp", "architect"}
    bd_entry = category in {"商务", "增长", "产品"}

    hard_to_fill = critical or (
        category in {"AI/算法", "数据"} and has_any_keyword(text, ("llm", "ml", "algorithm", "infra", "platform"))
    )
    role_complexity = classify_role_complexity(text, bd_entry=bd_entry, hard_to_fill=hard_to_fill)
    business_criticality = classify_business_criticality(text, category=category)

    anomaly_signals: list[str] = []
    if job.posted_at and (now.date() - job.posted_at.date()).days >= LONG_RUNNING_DAYS:
        anomaly_signals.append("long_running")
    if count_keyword_hits(
        text,
        ("llm", "infra", "platform", "roadmap", "customer", "delivery", "partnership", "founding"),
    ) >= 4:
        anomaly_signals.append("wish_list_jd")

    time_pressure_signals: list[str] = []
    if urgent:
        time_pressure_signals.append("urgent")
    if "long_running" in anomaly_signals:
        time_pressure_signals.append("long_running")
    if "founding" in text:
        time_pressure_signals.append("founder_hiring")

    return JobFacts(
        title=job.title,
        category=category,
        domain_tag=domain_tag,
        seniority=seniority,
        urgent=urgent,
        critical=critical,
        bd_entry=bd_entry,
        hard_to_fill=hard_to_fill,
        role_complexity=role_complexity,
        business_criticality=business_criticality,
        anomaly_signals=tuple(anomaly_signals),
        compensation_signal=classify_compensation_signal(text),
        company_signal=classify_company_signal(domain_tag, text),
        time_pressure_signals=tuple(time_pressure_signals),
        annual_salary_range=parse_annual_salary_range(text),
    )


def build_v1_score_input(facts: JobFacts) -> JobScoreInput:
    return JobScoreInput(
        title=facts.title,
        category=facts.category,
        urgent=facts.urgent,
        critical=facts.critical,
        bd_entry=facts.bd_entry,
    )


def build_v2_score_input(facts: JobFacts) -> JobScoreV2Input:
    return JobScoreV2Input(
        seniority=facts.seniority,
        urgent=facts.urgent,
        critical=facts.critical,
        bd_entry=facts.bd_entry,
        hard_to_fill=facts.hard_to_fill,
        role_complexity=facts.role_complexity,
        business_criticality=facts.business_criticality,
        anomaly_signals=facts.anomaly_signals,
        category=facts.category,
        domain_tag=facts.domain_tag,
        compensation_signal=facts.compensation_signal,
        company_signal=facts.company_signal,
        time_pressure_signals=facts.time_pressure_signals,
    )


def build_legacy_signal_tags(facts: JobFacts) -> dict:
    return {
        "display_tags": build_display_tags(facts),
        "urgent": facts.urgent,
        "critical": facts.critical,
        "bd_entry": facts.bd_entry,
    }


def build_display_tags(facts: JobFacts) -> list[str]:
    display_tags: list[str] = []

    if facts.domain_tag in {"AI", "Web3", "金融/支付"}:
        display_tags.append(facts.domain_tag)
    display_tags.append(build_secondary_tag(facts))
    display_tags.append(build_opportunity_tag(facts))

    if "long_running" in facts.anomaly_signals:
        if len(display_tags) >= 3:
            display_tags[2] = "长期挂岗"
        else:
            display_tags.append("长期挂岗")

    return display_tags[:3]


def build_secondary_tag(facts: JobFacts) -> str:
    if facts.seniority != "none":
        return "Senior"
    if facts.category == "产品":
        return "产品"
    if facts.category == "商务":
        return "商务"
    if facts.category == "增长":
        return "增长"
    if facts.category == "数据":
        return "数据"
    return "技术"


def build_opportunity_tag(facts: JobFacts) -> str:
    if facts.critical or facts.seniority == "founding":
        return "核心岗位"
    if facts.bd_entry:
        return "高 BD 切入口"
    return "关键扩张"


def normalize_company_name(company: str) -> str:
    return " ".join(company.lower().split())


def derive_company_name(canonical_url: str) -> str:
    host = canonical_url.split("//")[-1].split("/")[0]
    stem = host.replace("www.", "").split(".")[0]
    words = [word for word in stem.replace("-", " ").replace("_", " ").split() if word]
    if not words:
        return "Unknown Company"
    return " ".join(word.capitalize() for word in words)


def classify_job_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if has_any_keyword(text, ("ai", "ml", "machine learning", "llm", "algorithm", "algorithms")):
        return "AI/算法"
    if has_any_keyword(text, ("data scientist", "data engineer", "analytics", "analyst")):
        return "数据"
    if "product" in text or "产品" in text:
        return "产品"
    if has_any_keyword(text, ("growth", "marketing", "go-to-market")):
        return "增长"
    if has_any_keyword(text, ("partnership", "business development", "ecosystem", "bd")):
        return "商务"
    if has_any_keyword(text, ("operations", "运营", "community")):
        return "运营"
    return "技术"


def classify_domain_tag(title: str, description: str, canonical_url: str) -> str:
    text = f"{title} {description} {canonical_url}".lower()
    if has_any_keyword(text, ("ai", "llm", "ml", "model", "agent")):
        return "AI"
    if has_any_keyword(text, ("web3", "crypto", "blockchain", "defi", "wallet")):
        return "Web3"
    if has_any_keyword(text, ("payment", "fintech", "banking")):
        return "金融/支付"
    return "工具/SaaS"


def classify_seniority(text: str) -> str:
    keyword_map = (
        ("vp", "vp"),
        ("vice president", "vp"),
        ("director", "director"),
        ("head", "head"),
        ("principal", "principal"),
        ("staff", "staff"),
        ("lead", "lead"),
        ("architect", "architect"),
        ("senior", "senior"),
        ("founding", "founding"),
    )
    for keyword, level in keyword_map:
        if keyword in text:
            return level
    return "none"


def classify_role_complexity(text: str, *, bd_entry: bool, hard_to_fill: bool) -> str:
    complexity_hits = count_keyword_hits(
        text,
        ("cross-functional", "partnership", "customer", "delivery", "roadmap", "infra", "platform"),
    )
    if hard_to_fill and complexity_hits >= 2:
        return "high"
    if complexity_hits >= 1 or bd_entry:
        return "medium"
    return "low"


def classify_business_criticality(text: str, *, category: str) -> str:
    if has_any_keyword(
        text,
        ("launch", "delivery", "revenue", "growth", "roadmap", "platform", "core", "founding"),
    ):
        return "high"
    if category in {"AI/算法", "产品", "增长"}:
        return "medium"
    return "low"


def classify_compensation_signal(text: str) -> str:
    if parse_annual_salary_range(text) is not None:
        return "strong"
    if has_any_keyword(text, ("k/月", "k per month", "$", "usd", "rmb", "salary", "compensation")):
        return "strong"
    return "unknown"


def parse_annual_salary_range(text: str) -> tuple[int, int] | None:
    normalized = text.lower().replace(",", "")
    monthly = _parse_salary_range(
        normalized,
        (
            r"(?:¥|rmb|cny)?\s*(\d+(?:\.\d+)?)\s*k\s*[-~－到]\s*(\d+(?:\.\d+)?)\s*k?\s*(?:/|per\s*)?(?:month|月|monthly)",
            r"(?:salary\s*range[:：]?\s*)?(?:¥|rmb|cny)?\s*(\d+(?:\.\d+)?)\s*[-~－到]\s*(\d+(?:\.\d+)?)\s*k\s*(?:/|per\s*)?(?:month|月|monthly)",
        ),
        multiplier=12_000,
    )
    if monthly is not None:
        return monthly

    annual = _parse_salary_range(
        normalized,
        (
            r"(?:¥|rmb|cny)?\s*(\d+(?:\.\d+)?)\s*k\s*[-~－到]\s*(\d+(?:\.\d+)?)\s*k?\s*(?:/|per\s*)?(?:year|annual|annually|年|yearly)",
        ),
        multiplier=1_000,
    )
    if annual is not None:
        return annual

    annual_wan = _parse_salary_range(
        normalized,
        (r"(?:年薪|annual\s+salary)\s*(?:¥|rmb|cny)?\s*(\d+(?:\.\d+)?)\s*[-~－到]\s*(\d+(?:\.\d+)?)\s*万",),
        multiplier=10_000,
    )
    if annual_wan is not None:
        return annual_wan

    return _parse_currency_annual_salary_range(normalized)


def _parse_salary_range(text: str, patterns: tuple[str, ...], *, multiplier: int) -> tuple[int, int] | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        low = int(float(match.group(1)) * multiplier)
        high = int(float(match.group(2)) * multiplier)
        return (min(low, high), max(low, high))
    return None


def _parse_currency_annual_salary_range(text: str) -> tuple[int, int] | None:
    match = re.search(
        r"\b(cny|rmb|usd|cad|eur|gbp|inr|thb|czk|brl)\s+(\d+(?:\.\d+)?)\s*k\s*[-~－到]\s*(\d+(?:\.\d+)?)\s*k\b",
        text,
    )
    if match is None:
        return None

    rate = CURRENCY_TO_CNY_RATE[match.group(1)]
    low = int(float(match.group(2)) * 1_000 * rate)
    high = int(float(match.group(3)) * 1_000 * rate)
    return (min(low, high), max(low, high))


def classify_company_signal(domain_tag: str, text: str) -> str:
    if domain_tag in {"AI", "Web3"} and has_any_keyword(text, ("founding", "backed", "funded", "series")):
        return "hot"
    if domain_tag in {"AI", "Web3"}:
        return "hot"
    return "neutral"


def has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)
