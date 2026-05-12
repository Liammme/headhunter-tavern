from __future__ import annotations

import json
from pathlib import Path
from typing import Any

JDTRUST_RISK_LEVELS = {"low", "needs_review", "high"}
EXCLUDED_SOURCE_NAMES = {"aijobsnet"}
DOMAIN_WARNING_LABELS = {
    ("email_domain_status", "mx_missing"): "邮箱域名缺少 MX 记录",
    ("email_domain_relation", "mismatches_company_domain"): "邮箱域名与公司域名不一致",
    ("email_domain_relation", "personal_email_provider"): "招聘邮箱使用个人邮箱服务",
    ("domain_age_status", "new_domain_30d"): "岗位页外部域名注册未满 30 天",
    ("domain_age_status", "new_domain_90d"): "岗位页外部域名注册未满 90 天",
}
REASON_WARNING_LABELS = {
    "rootdata_status_not_found": "RootData未命中",
    "identity_evidence_thin": "身份链偏薄",
    "apply_url_missing": "缺少申请入口",
    "source_internal_apply_needs_review": "站内申请需核验",
    "source_internal_company_url_needs_review": "来源站公司页需核验",
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
    ("apply_link_status", "external_present"): ("外部申请入口", "positive"),
    ("job_page_social_status", "links_present"): ("社交链接存在", "neutral"),
}
LINK_FACT_TAG_LABELS = {
    "ats_ashby": "Ashby申请入口",
    "ats_lever": "Lever申请入口",
    "ats_greenhouse": "Greenhouse申请入口",
    "apply_url": "外部申请入口",
    "company_url": "公司官网链接",
    "github": "GitHub链接",
    "twitter_x": "X账号链接",
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

    domain_warnings = _domain_warnings(row.get("reputation_facts"))

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


def _domain_warnings(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []

    warnings: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
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
        seen.add(key)
        warnings.append(
            {
                "fact_name": fact_name,
                "fact_value": fact_value,
                "label": label,
            }
        )
    return warnings


def _verification_tags(row: dict, *, reason_codes: list[str], domain_warnings: list[dict]) -> list[dict]:
    tags: list[dict] = []
    seen: set[tuple[str, str]] = set()

    evidence = row.get("evidence")
    if isinstance(evidence, dict):
        is_accessible = evidence.get("is_accessible")
        if is_accessible is False:
            _append_tag(tags, seen, "原帖不可访问", "danger")
        elif is_accessible is True:
            _append_tag(tags, seen, "原帖可访问", "positive")

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

    link_facts = row.get("link_facts")
    if isinstance(link_facts, list):
        for fact in link_facts:
            if not isinstance(fact, dict):
                continue
            kind = _optional_str(fact.get("kind"))
            if kind is None:
                continue
            label = LINK_FACT_TAG_LABELS.get(kind)
            if label is None and kind.startswith("ats_"):
                label = "ATS申请入口"
            if label is not None:
                _append_tag(tags, seen, label, "positive")

    tags.sort(key=lambda item: TAG_TONE_ORDER.get(item["tone"], len(TAG_TONE_ORDER)))
    return tags[:MAX_VERIFICATION_TAGS]


def _append_tag(tags: list[dict], seen: set[tuple[str, str]], label: str, tone: str) -> None:
    key = (label, tone)
    if key in seen:
        return
    seen.add(key)
    tags.append({"label": label, "tone": tone})
