from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from app.crawlers.base import NormalizedJob
from app.services.job_facts import extract_job_facts, standardize_job_input
from app.services.market_signal_builder import BUSINESS_KEYWORDS, TECH_KEYWORDS
from app.services.market_theme_classifier import classify_market_theme


@dataclass(frozen=True)
class ExtractedMarketIntelligenceFact:
    dedupe_key: str
    posted_at: datetime | None
    collected_at: datetime
    company: str | None
    company_normalized: str | None
    title: str
    job_function: str
    market_theme: str
    seniority: str
    tech_keywords: list[str]
    business_keywords: list[str]
    salary_signal: str
    fact_summary: str

    def to_model_payload(self) -> dict:
        return {
            "dedupe_key": self.dedupe_key,
            "posted_at": self.posted_at,
            "collected_at": self.collected_at,
            "company": self.company,
            "company_normalized": self.company_normalized,
            "title": self.title,
            "job_function": self.job_function,
            "market_theme": self.market_theme,
            "seniority": self.seniority,
            "tech_keywords": self.tech_keywords,
            "business_keywords": self.business_keywords,
            "salary_signal": self.salary_signal,
            "fact_summary": self.fact_summary,
        }


def extract_market_intelligence_fact(
    job: NormalizedJob,
    *,
    collected_at: datetime | None = None,
) -> ExtractedMarketIntelligenceFact | None:
    if not (job.title or "").strip():
        return None

    collected_at = (collected_at or datetime.now()).replace(microsecond=0)
    standardized = standardize_job_input(job, now=collected_at)
    if not standardized.title:
        return None

    facts = extract_job_facts(standardized, now=collected_at)
    description = standardized.description
    market_theme = classify_market_theme(standardized.title, description)
    tech_keywords = _extract_keywords(description, TECH_KEYWORDS)
    business_keywords = _extract_keywords(description, BUSINESS_KEYWORDS)
    company = standardized.company.strip() or None
    company_normalized = standardized.company_normalized.strip() or None

    return ExtractedMarketIntelligenceFact(
        dedupe_key=_build_dedupe_key(job, standardized.title, company),
        posted_at=standardized.posted_at,
        collected_at=standardized.collected_at,
        company=company,
        company_normalized=company_normalized,
        title=standardized.title,
        job_function=facts.category,
        market_theme=market_theme,
        seniority=facts.seniority,
        tech_keywords=tech_keywords,
        business_keywords=business_keywords,
        salary_signal=facts.compensation_signal,
        fact_summary=_build_fact_summary(
            market_theme=market_theme,
            job_function=facts.category,
            seniority=facts.seniority,
            tech_keywords=tech_keywords,
            business_keywords=business_keywords,
            salary_signal=facts.compensation_signal,
        ),
    )


def _build_dedupe_key(job: NormalizedJob, title: str, company: str | None) -> str:
    canonical_url = (job.canonical_url or "").strip()
    if canonical_url:
        basis = f"url:{canonical_url}"
    else:
        basis = f"job:{job.source_job_id or ''}|{company or ''}|{title}"
    return sha256(basis.encode("utf-8")).hexdigest()


def _extract_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _build_fact_summary(
    *,
    market_theme: str,
    job_function: str,
    seniority: str,
    tech_keywords: list[str],
    business_keywords: list[str],
    salary_signal: str,
) -> str:
    keywords = [*tech_keywords, *business_keywords][:5]
    parts = [market_theme, job_function]
    if seniority != "none":
        parts.append(seniority)
    if keywords:
        parts.append(", ".join(keywords))
    if salary_signal != "unknown":
        parts.append(f"salary_signal={salary_signal}")
    return " | ".join(parts)
