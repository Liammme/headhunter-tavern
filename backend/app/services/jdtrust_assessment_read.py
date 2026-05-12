from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

JDTRUST_RISK_LEVELS = {"low", "needs_review", "high"}
EXCLUDED_SOURCE_NAMES = {"aijobsnet"}
SOURCE_SITE_DOMAINS = {
    "aijobs.net",
    "cryptocurrencyjobs.co",
    "cryptojobslist.com",
    "dejob.ai",
    "web3.career",
}
DOMAIN_WARNING_LABELS = {
    ("email_domain_status", "mx_missing"): "邮箱域名缺少 MX 记录",
    ("email_domain_relation", "mismatches_company_domain"): "邮箱域名与公司域名不一致",
    ("email_domain_relation", "personal_email_provider"): "招聘邮箱使用个人邮箱服务",
    ("domain_age_status", "new_domain_30d"): "项目域名注册未满 30 天",
    ("domain_age_status", "new_domain_90d"): "项目域名注册未满 90 天",
}
DOMAIN_AGE_POSITIVE_LABELS = {
    "older_than_30d": "官网域名注册超过 1 个月",
    "over_30d": "官网域名注册超过 1 个月",
    "gt_30d": "官网域名注册超过 1 个月",
    "older_than_1y": "官网域名注册超过 1 年",
    "over_1y": "官网域名注册超过 1 年",
    "gt_1y": "官网域名注册超过 1 年",
}
TAG_DESCRIPTIONS = {
    "RootData命中": "在 RootData 中找到了与公司/项目匹配的记录，可作为外部身份佐证。",
    "RootData未命中": "RootData 未找到匹配记录，不代表一定有风险，但需要更多外部佐证。",
    "CMC命中": "在 CoinMarketCap 中找到了匹配记录，可作为项目公开资料佐证。",
    "GitHub活跃": "关联 GitHub 存在近期活动，可作为项目持续维护的佐证。",
    "X账号已验证": "关联 X/Twitter 账号通过外部验证，可作为公开身份佐证。",
    "外部社交已验证": "关联社交账号通过外部验证，可作为公开身份佐证。",
    "身份链较强": "岗位页、公司链接、社交或外部声誉信息之间有较多一致佐证。",
    "身份证据一般": "找到部分身份佐证，但还不足以形成强确认。",
    "身份链偏薄": "当前岗位页缺少足够的公司/项目外部佐证，建议进一步核验。",
    "邮箱域名缺少 MX 记录": "招聘邮箱域名缺少邮件服务记录，可能需要核验邮箱真实性。",
    "邮箱域名与公司域名不一致": "招聘邮箱域名和公司域名不一致，需要确认是否为官方招聘渠道。",
    "招聘邮箱使用个人邮箱服务": "招聘邮箱使用个人邮箱服务，建议确认是否为官方联系人。",
    "项目域名注册未满 30 天": "项目相关域名注册时间很短，需要额外核验来源。",
    "项目域名注册未满 90 天": "项目相关域名注册时间较短，建议结合其他证据判断。",
    "官网域名注册超过 1 个月": "原帖抓到了项目官网，并确认该官网域名注册时间超过 1 个月。",
    "官网域名注册超过 1 年": "原帖抓到了项目官网，并确认该官网域名注册时间超过 1 年。",
}
REASON_WARNING_LABELS = {
    "rootdata_status_not_found": "RootData未命中",
    "identity_evidence_thin": "身份链偏薄",
}
REPUTATION_TAG_LABELS = {
    ("rootdata_status", "matched"): ("RootData命中", "positive"),
    ("rootdata_status", "not_found"): ("RootData未命中", "warning"),
    ("cmc_status", "matched"): ("CMC命中", "positive"),
    ("github_status", "active"): ("GitHub活跃", "positive"),
    ("x_status", "active_verified"): ("X账号已验证", "positive"),
    ("external_social_status", "active_verified"): ("外部社交已验证", "positive"),
    ("identity_evidence", "strong"): ("身份链较强", "positive"),
    ("identity_evidence", "moderate"): ("身份证据一般", "neutral"),
    ("identity_evidence", "thin"): ("身份链偏薄", "warning"),
}
TAG_TONE_ORDER = {"danger": 0, "warning": 1, "positive": 2, "neutral": 3}
MAX_VERIFICATION_TAGS = 4


def load_jdtrust_assessments(path: str | Path | None) -> dict[int, dict]:
    if path is None:
        return {}

    assessment_path = Path(path)
    if not assessment_path.exists() or not assessment_path.is_file():
        return {}

    assessments: dict[int, dict] = {}
    with assessment_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            assessment = _parse_assessment_line(line)
            if assessment is not None:
                assessments[assessment["legacy_job_id"]] = assessment
    return assessments


def _parse_assessment_line(line: str) -> dict | None:
    if not line.strip():
        return None

    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        return None

    if not isinstance(row, dict):
        return None

    legacy_job_id = _coerce_int(row.get("legacy_job_id"))
    source_name = _optional_str(row.get("source_name"))
    combined_assessment = row.get("combined_assessment")
    if legacy_job_id is None or not isinstance(combined_assessment, dict):
        return None
    if source_name and source_name.lower() in EXCLUDED_SOURCE_NAMES:
        return None

    risk_level = combined_assessment.get("risk_level")
    if risk_level not in JDTRUST_RISK_LEVELS:
        return None

    project_website_domains = _project_website_domains(row)
    domain_warnings = _domain_warnings(row.get("reputation_facts"), row, project_website_domains)

    return {
        "legacy_job_id": legacy_job_id,
        "canonical_url": _optional_str(row.get("canonical_url")),
        "source_name": source_name,
        "title": _optional_str(row.get("title")),
        "company": _optional_str(row.get("company")),
        "risk_level": risk_level,
        "trust_score": _coerce_int(combined_assessment.get("trust_score")),
        "reason_codes": _string_list(combined_assessment.get("reason_codes")),
        "recommended_checks": _string_list(combined_assessment.get("recommended_checks")),
        "evidence_refs": _string_list(combined_assessment.get("evidence_refs")),
        "domain_warnings": domain_warnings,
        "verification_tags": _verification_tags(
            row,
            reason_codes=_string_list(combined_assessment.get("reason_codes")),
            domain_warnings=domain_warnings,
            project_website_domains=project_website_domains,
        ),
    }


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _domain_warnings(value: Any, row: dict | None = None, project_website_domains: set[str] | None = None) -> list[dict]:
    if not isinstance(value, list):
        return []

    project_website_domains = project_website_domains or set()
    warnings: list[dict] = []
    seen: set[tuple[str, str]] = set()
    domain_age_facts = _combined_domain_age_facts(value)
    for item in [*value, *domain_age_facts]:
        if not isinstance(item, dict):
            continue
        fact_name = _optional_str(item.get("fact_name"))
        fact_value = _optional_str(item.get("fact_value"))
        if fact_name is None or fact_value is None:
            continue
        key = (fact_name, fact_value)
        label = DOMAIN_WARNING_LABELS.get(key)
        if label is None or key in seen:
            continue
        if _is_source_site_domain_fact(item, row):
            continue
        if fact_name == "domain_age_status" and not _is_project_website_domain_fact(item, project_website_domains):
            continue
        seen.add(key)
        warnings.append(
            {
                "fact_name": fact_name,
                "fact_value": fact_value,
                "label": label,
            }
        )
    return warnings


def _project_website_domains(row: dict) -> set[str]:
    link_facts = row.get("link_facts")
    if not isinstance(link_facts, list):
        return set()

    domains: set[str] = set()
    for item in link_facts:
        if not isinstance(item, dict):
            continue
        if _optional_str(item.get("kind")) != "company_url":
            continue
        domain = _fact_domain(item)
        if domain is None or _is_source_site_domain(domain, row):
            continue
        domains.add(domain)
    return domains


def _is_project_website_domain_fact(item: dict, project_website_domains: set[str]) -> bool:
    domain = _fact_domain(item)
    if domain is None:
        return False
    return any(domain == project_domain or domain.endswith(f".{project_domain}") for project_domain in project_website_domains)


def _is_source_site_domain_fact(item: dict, row: dict | None) -> bool:
    domain = _fact_domain(item)
    if domain is None:
        return False
    return _is_source_site_domain(domain, row)


def _is_source_site_domain(domain: str, row: dict | None) -> bool:
    source_domains = set(SOURCE_SITE_DOMAINS)
    if row is not None:
        canonical_domain = _domain_from_url(_optional_str(row.get("canonical_url")))
        if canonical_domain is not None:
            source_domains.add(canonical_domain)

    return any(domain == source_domain or domain.endswith(f".{source_domain}") for source_domain in source_domains)


def _fact_domain(item: dict) -> str | None:
    for key in ("domain", "hostname", "host", "subject_domain", "email_domain", "company_domain", "registered_domain"):
        domain = _normalize_domain(_optional_str(item.get(key)))
        if domain is not None:
            return domain

    for key in ("url", "final_url", "evidence"):
        domain = _domain_from_url(_optional_str(item.get(key)))
        if domain is not None:
            return domain

    return None


def _domain_from_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    return _normalize_domain(parsed.netloc)


def _normalize_domain(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    if "://" in cleaned:
        return _domain_from_url(cleaned)
    cleaned = cleaned.split("/", 1)[0].split(":", 1)[0]
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    return cleaned or None


def _verification_tags(
    row: dict,
    *,
    reason_codes: list[str],
    domain_warnings: list[dict],
    project_website_domains: set[str],
) -> list[dict]:
    tags: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for warning in domain_warnings:
        label = _optional_str(warning.get("label"))
        if label is not None:
            _append_tag(tags, seen, label, "warning")

    for code in reason_codes:
        label = REASON_WARNING_LABELS.get(code)
        if label is not None:
            _append_tag(tags, seen, label, "warning")

    reputation_facts = row.get("reputation_facts")
    if isinstance(reputation_facts, list):
        for fact in reputation_facts:
            if not isinstance(fact, dict):
                continue
            fact_name = _optional_str(fact.get("fact_name"))
            fact_value = _optional_str(fact.get("fact_value"))
            if fact_name is None or fact_value is None:
                continue
            tag = REPUTATION_TAG_LABELS.get((fact_name, fact_value))
            if tag is not None:
                _append_tag(tags, seen, tag[0], tag[1])
            domain_age_label = _domain_age_positive_label(fact, fact_name, fact_value, project_website_domains)
            if domain_age_label is not None:
                _append_tag(tags, seen, domain_age_label, "positive")
        for fact in _combined_domain_age_facts(reputation_facts):
            domain_age_label = _domain_age_positive_label(
                fact,
                _optional_str(fact.get("fact_name")) or "",
                _optional_str(fact.get("fact_value")) or "",
                project_website_domains,
            )
            if domain_age_label is not None:
                _append_tag(tags, seen, domain_age_label, "positive")

    tags.sort(key=lambda item: TAG_TONE_ORDER.get(item["tone"], len(TAG_TONE_ORDER)))
    return tags[:MAX_VERIFICATION_TAGS]


def _combined_domain_age_facts(reputation_facts: list) -> list[dict]:
    status: str | None = None
    domain: str | None = None
    age_days: str | None = None
    for fact in reputation_facts:
        if not isinstance(fact, dict):
            continue
        fact_name = _optional_str(fact.get("fact_name"))
        fact_value = _optional_str(fact.get("fact_value"))
        if fact_name is None or fact_value is None:
            continue
        if fact_name == "domain_age_status":
            status = fact_value
        elif fact_name in {"domain_age_domain", "registered_domain"} and domain is None:
            domain = fact_value
        elif fact_name in {"domain_age_days", "age_days"} and age_days is None:
            age_days = fact_value

    if status is None or domain is None:
        return []

    return [
        {
            "fact_name": "domain_age_status",
            "fact_value": status,
            "domain": domain,
            "domain_age_days": age_days,
        }
    ]


def _domain_age_positive_label(
    fact: dict,
    fact_name: str,
    fact_value: str,
    project_website_domains: set[str],
) -> str | None:
    if fact_name != "domain_age_status" or not _is_project_website_domain_fact(fact, project_website_domains):
        return None

    age_days = _coerce_int(fact.get("domain_age_days") or fact.get("age_days") or fact.get("days_since_registration"))
    if age_days is not None:
        if age_days >= 365:
            return "官网域名注册超过 1 年"
        if age_days >= 30:
            return "官网域名注册超过 1 个月"

    if fact_value == "established":
        return "官网域名注册超过 1 个月"
    return DOMAIN_AGE_POSITIVE_LABELS.get(fact_value)


def _append_tag(tags: list[dict], seen: set[tuple[str, str]], label: str, tone: str) -> None:
    key = (label, tone)
    if key in seen:
        return
    seen.add(key)
    tags.append({"label": label, "tone": tone, "description": TAG_DESCRIPTIONS.get(label, label)})
