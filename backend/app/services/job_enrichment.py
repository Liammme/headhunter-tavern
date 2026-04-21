from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob
from app.services.scoring import derive_job_grade


def build_job_payload(job: NormalizedJob) -> dict:
    title = (job.title or "").strip()
    description = (job.description or "").strip()[:4000]
    company = (job.company or "").strip() or derive_company_name(job.canonical_url)
    company_normalized = normalize_company_name(company)
    job_category = classify_job_category(title, description)
    domain_tag = classify_domain_tag(title, description, job.canonical_url)
    signal_tags = build_signal_tags(title, description, job_category, domain_tag, job.posted_at)
    bounty_grade = derive_job_grade(title=title, category=job_category, signals=signal_tags)

    return {
        "canonical_url": job.canonical_url,
        "source_name": getattr(job, "source_name", None)
        or (job.raw_payload.get("site") if isinstance(job.raw_payload, dict) else "")
        or "crawler",
        "title": title,
        "company": company,
        "company_normalized": company_normalized,
        "description": description,
        "posted_at": job.posted_at,
        "collected_at": datetime.now().replace(microsecond=0),
        "job_category": job_category,
        "domain_tag": domain_tag,
        "bounty_grade": bounty_grade,
        "signal_tags": signal_tags,
    }


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
    if any(keyword in text for keyword in ("ai", "ml", "machine learning", "llm", "algorithm", "algorithms")):
        return "AI/算法"
    if any(keyword in text for keyword in ("data scientist", "data engineer", "analytics", "analyst")):
        return "数据"
    if "product" in text or "产品" in text:
        return "产品"
    if any(keyword in text for keyword in ("growth", "marketing", "go-to-market")):
        return "增长"
    if any(keyword in text for keyword in ("partnership", "business development", "ecosystem", "bd")):
        return "商务"
    if any(keyword in text for keyword in ("operations", "运营", "community")):
        return "运营"
    return "技术"


def classify_domain_tag(title: str, description: str, canonical_url: str) -> str:
    text = f"{title} {description} {canonical_url}".lower()
    if any(keyword in text for keyword in ("ai", "llm", "ml", "model", "agent")):
        return "AI"
    if any(keyword in text for keyword in ("web3", "crypto", "blockchain", "defi", "wallet")):
        return "Web3"
    if any(keyword in text for keyword in ("payment", "fintech", "banking")):
        return "金融/支付"
    return "工具/SaaS"


def build_signal_tags(
    title: str,
    description: str,
    job_category: str,
    domain_tag: str,
    posted_at: datetime | None,
) -> dict:
    text = f"{title} {description}".lower()
    display_tags: list[str] = []

    if domain_tag in {"AI", "Web3", "金融/支付"}:
        display_tags.append(domain_tag)
    if any(keyword in text for keyword in ("staff", "lead", "head", "principal", "architect", "senior")):
        display_tags.append("Senior")
    elif job_category == "产品":
        display_tags.append("产品")
    elif job_category == "商务":
        display_tags.append("商务")
    elif job_category == "增长":
        display_tags.append("增长")
    elif job_category == "数据":
        display_tags.append("数据")
    else:
        display_tags.append("技术")

    if any(keyword in text for keyword in ("staff", "lead", "head", "principal", "architect", "founding")):
        display_tags.append("核心岗位")
    elif job_category in {"商务", "增长", "产品"}:
        display_tags.append("高 BD 切入口")
    else:
        display_tags.append("关键扩张")

    urgent = any(keyword in text for keyword in ("urgent", "asap", "immediately", "hiring fast"))
    critical = any(keyword in text for keyword in ("lead", "head", "principal", "staff", "director", "architect"))
    bd_entry = job_category in {"商务", "增长", "产品"}

    if posted_at and posted_at.date() <= (datetime.now().date() - timedelta(days=7)):
        if len(display_tags) >= 3:
            display_tags[2] = "长期挂岗"
        else:
            display_tags.append("长期挂岗")

    return {
        "display_tags": display_tags[:3],
        "urgent": urgent,
        "critical": critical,
        "bd_entry": bd_entry,
    }
