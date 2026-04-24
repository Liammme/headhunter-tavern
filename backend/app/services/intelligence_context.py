from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from app.models import Job
from app.services.feed_snapshot import FeedMetadata

JOB_GRADE_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_intelligence_change_context(*, jobs: list[Job], meta: FeedMetadata) -> dict:
    window_start = date.fromisoformat(meta.window_start)
    today = date.fromisoformat(meta.window_end)
    yesterday = today - timedelta(days=1)
    window_jobs = [job for job in jobs if window_start <= _effective_date(job) <= today]
    today_jobs = [job for job in window_jobs if _effective_date(job) == today]
    yesterday_jobs = [job for job in window_jobs if _effective_date(job) == yesterday]
    baseline_jobs = [job for job in window_jobs if window_start <= _effective_date(job) < yesterday]
    baseline_day_count = max((yesterday - window_start).days, 1)

    today_counts = _build_counts(today_jobs)
    yesterday_counts = _build_counts(yesterday_jobs)
    baseline_counts = _build_counts(baseline_jobs)
    new_companies_today = _build_new_companies_today(
        today_jobs=today_jobs,
        historical_jobs=[*yesterday_jobs, *baseline_jobs],
    )
    rising_companies = _build_rising_companies(
        today_jobs=today_jobs,
        yesterday_jobs=yesterday_jobs,
        baseline_jobs=baseline_jobs,
        new_company_keys={item["company_key"] for item in new_companies_today},
        baseline_day_count=baseline_day_count,
    )
    top_rising_categories = _build_rising_dimensions(
        dimension_name="category",
        field_name="job_category",
        today_jobs=today_jobs,
        yesterday_jobs=yesterday_jobs,
        baseline_jobs=baseline_jobs,
        baseline_day_count=baseline_day_count,
    )
    top_rising_domains = _build_rising_dimensions(
        dimension_name="domain_tag",
        field_name="domain_tag",
        today_jobs=today_jobs,
        yesterday_jobs=yesterday_jobs,
        baseline_jobs=baseline_jobs,
        baseline_day_count=baseline_day_count,
    )

    representative_changes = _build_representative_changes(
        new_companies_today=new_companies_today,
        rising_companies=rising_companies,
        top_rising_categories=top_rising_categories,
        top_rising_domains=top_rising_domains,
    )

    return {
        "today_counts": today_counts,
        "yesterday_counts": yesterday_counts,
        "baseline_counts": baseline_counts,
        "deltas": {
            "today_vs_yesterday": _build_delta(today_counts, yesterday_counts),
            "today_vs_baseline_total": _build_delta(today_counts, baseline_counts),
        },
        "new_companies_today": _strip_internal_company_keys(new_companies_today),
        "rising_companies": _strip_internal_company_keys(rising_companies),
        "top_rising_categories": top_rising_categories,
        "top_rising_domains": top_rising_domains,
        "representative_changes": representative_changes,
    }


def _effective_date(job: Job) -> date:
    return (job.posted_at or job.collected_at).date()


def _company_key(job: Job) -> str:
    return (job.company_normalized or job.company).strip().lower()


def _safe_dimension(value: str | None) -> str:
    return value or "其他"


def _job_tags(job: Job) -> list[str]:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    return list(signal_tags.get("display_tags", []))


def _build_counts(jobs: list[Job]) -> dict:
    company_keys = {_company_key(job) for job in jobs}
    category_counts = Counter(_safe_dimension(job.job_category) for job in jobs)
    domain_counts = Counter(_safe_dimension(job.domain_tag) for job in jobs)
    company_counts = Counter(_company_key(job) for job in jobs)
    return {
        "job_count": len(jobs),
        "company_count": len(company_keys),
        "high_bounty_job_count": sum(1 for job in jobs if job.bounty_grade == "high"),
        "category_counts": dict(sorted(category_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "company_counts": dict(sorted(company_counts.items())),
    }


def _build_delta(left: dict, right: dict) -> dict:
    return {
        "job_count": left["job_count"] - right["job_count"],
        "company_count": left["company_count"] - right["company_count"],
        "high_bounty_job_count": left["high_bounty_job_count"] - right["high_bounty_job_count"],
    }


def _build_new_companies_today(*, today_jobs: list[Job], historical_jobs: list[Job]) -> list[dict]:
    historical_company_keys = {_company_key(job) for job in historical_jobs}
    grouped = _group_jobs_by_company(today_jobs)
    items = []
    for company_key, company_jobs in grouped.items():
        if company_key in historical_company_keys:
            continue
        sorted_jobs = _sort_jobs_for_evidence(company_jobs)
        items.append(
            {
                "company_key": company_key,
                "company": sorted_jobs[0].company,
                "today_count": len(company_jobs),
                "evidence": [_build_evidence(job, bucket="today") for job in sorted_jobs[:3]],
            }
        )

    return sorted(items, key=lambda item: (-item["today_count"], item["company"].lower()))[:5]


def _build_rising_companies(
    *,
    today_jobs: list[Job],
    yesterday_jobs: list[Job],
    baseline_jobs: list[Job],
    new_company_keys: set[str],
    baseline_day_count: int,
) -> list[dict]:
    today_grouped = _group_jobs_by_company(today_jobs)
    yesterday_counts = Counter(_company_key(job) for job in yesterday_jobs)
    baseline_counts = Counter(_company_key(job) for job in baseline_jobs)
    items = []
    for company_key, company_jobs in today_grouped.items():
        if company_key in new_company_keys:
            continue
        today_count = len(company_jobs)
        yesterday_count = yesterday_counts[company_key]
        baseline_daily_avg = baseline_counts[company_key] / baseline_day_count
        if today_count <= yesterday_count or today_count <= baseline_daily_avg:
            continue
        sorted_jobs = _sort_jobs_for_evidence(company_jobs)
        items.append(
            {
                "company_key": company_key,
                "company": sorted_jobs[0].company,
                "today_count": today_count,
                "yesterday_count": yesterday_count,
                "baseline_count": baseline_counts[company_key],
                "baseline_daily_avg": round(baseline_daily_avg, 2),
                "delta_vs_yesterday": today_count - yesterday_count,
                "evidence": [_build_evidence(job, bucket="today") for job in sorted_jobs[:3]],
            }
        )

    return sorted(
        items,
        key=lambda item: (-item["delta_vs_yesterday"], -item["today_count"], item["company"].lower()),
    )[:5]


def _build_rising_dimensions(
    *,
    dimension_name: str,
    field_name: str,
    today_jobs: list[Job],
    yesterday_jobs: list[Job],
    baseline_jobs: list[Job],
    baseline_day_count: int,
) -> list[dict]:
    today_counts = Counter(_safe_dimension(getattr(job, field_name)) for job in today_jobs)
    yesterday_counts = Counter(_safe_dimension(getattr(job, field_name)) for job in yesterday_jobs)
    baseline_counts = Counter(_safe_dimension(getattr(job, field_name)) for job in baseline_jobs)
    today_grouped: dict[str, list[Job]] = defaultdict(list)
    for job in today_jobs:
        today_grouped[_safe_dimension(getattr(job, field_name))].append(job)

    items = []
    for value, today_count in today_counts.items():
        baseline_daily_avg = baseline_counts[value] / baseline_day_count
        if today_count <= yesterday_counts[value] or today_count <= baseline_daily_avg:
            continue
        sorted_jobs = _sort_jobs_for_evidence(today_grouped[value])
        items.append(
            {
                dimension_name: value,
                "today_count": today_count,
                "yesterday_count": yesterday_counts[value],
                "baseline_count": baseline_counts[value],
                "baseline_daily_avg": round(baseline_daily_avg, 2),
                "delta_vs_yesterday": today_count - yesterday_counts[value],
                "evidence": [_build_evidence(job, bucket="today") for job in sorted_jobs[:3]],
            }
        )

    return sorted(
        items,
        key=lambda item: (-item["delta_vs_yesterday"], -item["today_count"], str(item[dimension_name]).lower()),
    )[:5]


def _group_jobs_by_company(jobs: list[Job]) -> dict[str, list[Job]]:
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[_company_key(job)].append(job)
    return grouped


def _sort_jobs_for_evidence(jobs: list[Job]) -> list[Job]:
    return sorted(
        jobs,
        key=lambda job: (
            JOB_GRADE_ORDER.get(job.bounty_grade, 3),
            job.company.lower(),
            job.title.lower(),
            job.canonical_url,
        ),
    )


def _build_evidence(job: Job, *, bucket: str) -> dict:
    return {
        "company": job.company,
        "title": job.title,
        "canonical_url": job.canonical_url,
        "bucket": bucket,
        "bounty_grade": job.bounty_grade,
        "tags": _job_tags(job),
        "category": _safe_dimension(job.job_category),
        "domain_tag": _safe_dimension(job.domain_tag),
    }


def _build_representative_changes(
    *,
    new_companies_today: list[dict],
    rising_companies: list[dict],
    top_rising_categories: list[dict],
    top_rising_domains: list[dict],
) -> list[dict]:
    changes: list[dict] = []
    for item in new_companies_today[:2]:
        changes.append(
            {
                "change_type": "new_company_today",
                "summary": f"{item['company']} 今天首次进入近 14 天窗口。",
                "evidence": item["evidence"],
            }
        )
    for item in rising_companies[:2]:
        changes.append(
            {
                "change_type": "rising_company",
                "summary": f"{item['company']} 今天岗位数相对昨天升温。",
                "evidence": item["evidence"],
            }
        )
    for item in top_rising_categories[:2]:
        changes.append(
            {
                "change_type": "rising_category",
                "summary": f"{item['category']} 今天相对昨天和基线升温。",
                "evidence": item["evidence"],
            }
        )
    for item in top_rising_domains[:2]:
        changes.append(
            {
                "change_type": "rising_domain",
                "summary": f"{item['domain_tag']} 今天相对昨天和基线升温。",
                "evidence": item["evidence"],
            }
        )

    if not changes:
        return [
            {
                "change_type": "no_today_change",
                "summary": "今天暂无可验证的新变化，情报应降级为稳定提示。",
                "evidence": [],
            }
        ]
    return changes[:5]


def _strip_internal_company_keys(items: list[dict]) -> list[dict]:
    return [{key: value for key, value in item.items() if key != "company_key"} for item in items]
