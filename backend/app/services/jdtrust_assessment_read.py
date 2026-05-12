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
        "domain_warnings": _domain_warnings(row.get("reputation_facts")),
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
