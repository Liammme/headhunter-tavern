import json
import re
from datetime import datetime
from typing import Any

from app.services.llm_client import request_structured_json, should_use_llm
from app.services.market_intelligence_report import parse_market_intelligence_report

KIND = "living_market_report"
SCHEMA_VERSION = "living-market-report-v1"
SECTION_IDS = {"market_structure", "demand_shifts", "company_patterns", "risk_and_uncertainty"}
STATUSES = {"new", "reinforced", "weakened", "retired"}
CONFIDENCES = {"low", "medium", "high"}
TOP_LEVEL_FIELDS = {
    "kind",
    "schema_version",
    "headline",
    "version",
    "mode",
    "previous_snapshot_id",
    "seed_window_days",
    "generated_at",
    "executive_summary",
    "sections",
    "claims",
    "watchlist",
    "data_quality",
}
BANNED_TEXT = (
    "猎头",
    "赏金",
    "认领",
    "客户开发",
    "岗位来源",
    "岗位链接",
    "canonical_url",
    "source_name",
    "full JD",
    "完整 JD",
    "原始链接",
    "bd_entry",
    "job_url",
    "full_description",
)
BANNED_FIELDS = {
    "canonical_url",
    "source_name",
    "source_url",
    "job_url",
    "full_description",
    "description",
    "bounty_grade",
    "claimed_names",
    "claim_status",
    "bd_entry",
    "signal_tags",
}
BANNED_TOKENS = {"bounty", "claimed"}


class LivingMarketReportError(Exception):
    pass


def build_living_market_report_system_prompt() -> str:
    return (
        "你从脱敏招聘事实生成中文 Living Market Report，只返回 JSON object，不要 Markdown。"
        "目标 1500-2500 字，不写日报、不写榜单、不写岗位流水账。"
        "只能使用输入 JSON 中的统计和 evidence_id；每个 claim 必须有 evidence_ids。"
        "禁止补外部事实，禁止输出 canonical_url/source_name/job_url/full_description、猎头、赏金、认领、客户开发、岗位来源、岗位链接。"
        "字段必须匹配 living_market_report schema，必须包含 headline，status 只能是 new/reinforced/weakened/retired。"
    )


def build_living_market_report_user_prompt(input_payload: dict) -> str:
    return "生成完整活报告 JSON：\n\n" + json.dumps(input_payload, ensure_ascii=False, sort_keys=True)


def generate_living_market_report_payload(
    input_payload: dict,
    *,
    version: int,
    mode: str,
    previous_snapshot_id: int | None,
    generated_at: datetime,
) -> dict:
    if not should_use_llm():
        return build_rule_living_market_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )

    messages = [
        {"role": "system", "content": build_living_market_report_system_prompt()},
        {"role": "user", "content": build_living_market_report_user_prompt(input_payload)},
    ]
    for attempt in range(2):
        try:
            content = request_structured_json(messages)
            report = parse_market_intelligence_report(content)
            report["version"] = version
            report["mode"] = mode
            report["previous_snapshot_id"] = previous_snapshot_id
            report["seed_window_days"] = 180
            report["generated_at"] = generated_at.replace(microsecond=0).isoformat()
            validate_living_market_report(report, input_payload=input_payload, expected_version=version)
            return report
        except Exception as exc:
            messages.append(
                {
                    "role": "user",
                    "content": f"上次输出未通过校验：{str(exc)[:300]}。只修 JSON/schema，不添加输入外事实。",
                }
            )
            if attempt == 0:
                continue
    return build_rule_living_market_report(
        input_payload,
        version=version,
        mode=mode,
        previous_snapshot_id=previous_snapshot_id,
        generated_at=generated_at,
    )


def validate_living_market_report(payload: dict, *, input_payload: dict, expected_version: int) -> None:
    if not isinstance(payload, dict):
        raise LivingMarketReportError("report must be a JSON object")
    extra = set(payload) - TOP_LEVEL_FIELDS
    if extra:
        raise LivingMarketReportError(f"unknown fields: {sorted(extra)}")
    _reject_leakage(payload)
    if payload.get("kind") != KIND:
        raise LivingMarketReportError("kind is invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise LivingMarketReportError("schema_version is invalid")
    _str(payload, "headline")
    if payload.get("version") != expected_version:
        raise LivingMarketReportError("version is invalid")
    if expected_version == 1 and "180d" not in _dict(input_payload, "market_windows"):
        raise LivingMarketReportError("v1 requires 180d window")
    if expected_version > 1 and not isinstance(input_payload.get("previous_report"), dict):
        raise LivingMarketReportError("v2 requires previous_report")

    sections = _list(payload, "sections")
    claims = _list(payload, "claims")
    if not 3 <= len(sections) <= 5:
        raise LivingMarketReportError("sections must contain 3 to 5 items")
    if not 4 <= len(claims) <= 10:
        raise LivingMarketReportError("claims must contain 4 to 10 items")

    allowed_evidence = _allowed_evidence_ids(input_payload)
    previous_claims = _previous_claim_ids(input_payload)
    claim_ids: set[str] = set()
    retired_claim_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise LivingMarketReportError("claims must contain objects")
        claim_id = _str(claim, "claim_id")
        claim_ids.add(claim_id)
        status = _str(claim, "status")
        if status not in STATUSES:
            raise LivingMarketReportError("status is invalid")
        if status == "retired":
            retired_claim_ids.add(claim_id)
        previous_claim_id = claim.get("previous_claim_id")
        if status != "new":
            if not isinstance(previous_claim_id, str) or not previous_claim_id.strip():
                raise LivingMarketReportError("previous_claim_id is required")
            if previous_claims and previous_claim_id not in previous_claims:
                raise LivingMarketReportError("previous_claim_id is unknown")
        confidence = _str(claim, "confidence")
        if confidence not in CONFIDENCES:
            raise LivingMarketReportError("confidence is invalid")
        evidence_ids = _str_list(claim, "evidence_ids")
        if not evidence_ids or any(evidence_id not in allowed_evidence for evidence_id in evidence_ids):
            raise LivingMarketReportError("evidence_id is invalid")
        _str(claim, "claim")
        _str_list(claim, "evidence_notes")
        _str(claim, "change_reason")

    for section in sections:
        if not isinstance(section, dict):
            raise LivingMarketReportError("sections must contain objects")
        section_id = _str(section, "section_id")
        if section_id not in SECTION_IDS:
            raise LivingMarketReportError("section_id is invalid")
        section_claim_ids = _str_list(section, "claim_ids")
        if not section_claim_ids or any(claim_id not in claim_ids for claim_id in section_claim_ids):
            raise LivingMarketReportError("section claim_ids are invalid")
        if any(claim_id in retired_claim_ids for claim_id in section_claim_ids):
            raise LivingMarketReportError("retired claim cannot be section judgment")
        _str(section, "title")
        _str(section, "body")

    for item in _list(payload, "watchlist"):
        if not isinstance(item, dict):
            raise LivingMarketReportError("watchlist must contain objects")
        _str(item, "topic")
        _str(item, "why_watch")
        evidence_ids = _str_list(item, "evidence_ids")
        if any(evidence_id not in allowed_evidence for evidence_id in evidence_ids):
            raise LivingMarketReportError("watchlist evidence_id is invalid")
    if not isinstance(payload.get("data_quality"), dict):
        raise LivingMarketReportError("data_quality must be an object")


def build_rule_living_market_report(
    input_payload: dict,
    *,
    version: int,
    mode: str,
    previous_snapshot_id: int | None,
    generated_at: datetime,
) -> dict:
    evidence_id = next(iter(_allowed_evidence_ids(input_payload)), "e1")
    data_quality = input_payload.get("data_quality") if isinstance(input_payload.get("data_quality"), dict) else {}
    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "headline": "市场需求保持克制",
        "version": version,
        "mode": mode,
        "previous_snapshot_id": previous_snapshot_id,
        "seed_window_days": 180,
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "executive_summary": "当前样本支持保守的市场判断：结构性需求存在，但不足以证明整体市场全面升温。",
        "sections": [
            {"section_id": "market_structure", "title": "市场结构", "body": "市场结构仍以可见主题的稳定出现为主，需要避免把短期波动解释成全面扩张。", "claim_ids": ["c1"]},
            {"section_id": "demand_shifts", "title": "需求变化", "body": "短窗变化应放回 180 天基线中观察，目前更适合识别方向，而不是下强趋势结论。", "claim_ids": ["c2"]},
            {"section_id": "company_patterns", "title": "公司与组织信号", "body": "代表样本显示组织需求仍偏选择性补强，尚未形成广泛扩招信号。", "claim_ids": ["c3"]},
            {"section_id": "risk_and_uncertainty", "title": "不确定性", "body": "当前报告基于可见结构化事实，样本覆盖不等于完整市场历史。", "claim_ids": ["c4"]},
        ],
        "claims": [
            _rule_claim("c1", "结构性需求存在，但证据强度仍需保持克制。", evidence_id),
            _rule_claim("c2", "短期变化不足以证明市场全面升温。", evidence_id),
            _rule_claim("c3", "组织信号更像选择性补强。", evidence_id),
            _rule_claim("c4", "样本质量限制需要持续标注。", evidence_id),
        ],
        "watchlist": [{"topic": "结构性主题", "why_watch": "观察后续短窗是否持续扩大。", "evidence_ids": [evidence_id]}],
        "data_quality": data_quality,
    }


def _rule_claim(claim_id: str, claim: str, evidence_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "previous_claim_id": None,
        "status": "new",
        "claim": claim,
        "confidence": "low",
        "evidence_ids": [evidence_id],
        "evidence_notes": ["规则 fallback 使用输入中的结构化证据。"],
        "change_reason": "LLM 不可用或输出未通过校验，使用保守规则报告。",
    }


def _allowed_evidence_ids(input_payload: dict) -> set[str]:
    evidence_ids: set[str] = set()
    for field in ("new_facts", "representative_samples"):
        value = input_payload.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str):
                    evidence_ids.add(item["evidence_id"])
    return evidence_ids


def _previous_claim_ids(input_payload: dict) -> set[str]:
    previous_report = input_payload.get("previous_report")
    if not isinstance(previous_report, dict):
        return set()
    claims = previous_report.get("active_claims")
    if not isinstance(claims, list):
        return set()
    return {claim["claim_id"] for claim in claims if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)}


def _reject_leakage(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key in BANNED_FIELDS:
                raise LivingMarketReportError(f"banned field: {key}")
            _reject_leakage(item)
        return
    if isinstance(value, list):
        for item in value:
            _reject_leakage(item)
        return
    if isinstance(value, str):
        normalized = value.lower()
        for phrase in BANNED_TEXT:
            if phrase.lower() in normalized:
                raise LivingMarketReportError(f"banned phrase: {phrase}")
        for token in BANNED_TOKENS:
            if re.search(rf"(?<![a-z0-9-]){re.escape(token)}(?![a-z0-9-])", normalized):
                raise LivingMarketReportError(f"banned phrase: {token}")


def _dict(payload: dict, field: str) -> dict:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise LivingMarketReportError(f"{field} must be an object")
    return value


def _list(payload: dict, field: str) -> list:
    value = payload.get(field)
    if not isinstance(value, list):
        raise LivingMarketReportError(f"{field} must be a list")
    return value


def _str(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LivingMarketReportError(f"{field} must be a non-empty string")
    return value


def _str_list(payload: dict, field: str) -> list[str]:
    value = _list(payload, field)
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise LivingMarketReportError(f"{field} must be a list of non-empty strings")
    return value
