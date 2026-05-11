from __future__ import annotations

import json
from pathlib import Path
from typing import Any

JDTRUST_RISK_LEVELS = {"low", "needs_review", "high"}


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
    combined_assessment = row.get("combined_assessment")
    if legacy_job_id is None or not isinstance(combined_assessment, dict):
        return None

    risk_level = combined_assessment.get("risk_level")
    if risk_level not in JDTRUST_RISK_LEVELS:
        return None

    return {
        "legacy_job_id": legacy_job_id,
        "canonical_url": _optional_str(row.get("canonical_url")),
        "source_name": _optional_str(row.get("source_name")),
        "title": _optional_str(row.get("title")),
        "company": _optional_str(row.get("company")),
        "risk_level": risk_level,
        "trust_score": _coerce_int(combined_assessment.get("trust_score")),
        "reason_codes": _string_list(combined_assessment.get("reason_codes")),
        "recommended_checks": _string_list(combined_assessment.get("recommended_checks")),
        "evidence_refs": _string_list(combined_assessment.get("evidence_refs")),
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
