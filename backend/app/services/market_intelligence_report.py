import json
import re
from typing import Any

from app.services.llm_client import request_structured_json, should_use_llm


CONFIDENCE_VALUES = {"low", "medium", "high"}
PERSPECTIVE_LENSES = {"industry", "product_business", "organization_hiring"}
TREND_DIRECTIONS = {"rising", "cooling", "shifting", "stable", "emerging"}
TREND_TIME_HORIZONS = {"7d", "30d", "90d"}
BANNED_PHRASES = (
    "BD",
    "猎头",
    "赏金",
    "认领",
    "客户开发",
    "岗位来源",
    "岗位链接",
    "canonical_url",
    "source_name",
    "根据数据分析可得",
    "综合来看",
    "建议持续关注",
)


class MarketIntelligenceReportError(Exception):
    pass


def build_market_intelligence_system_prompt() -> str:
    return (
        "You write market intelligence reports from sanitized hiring signals. "
        "Return only a JSON object with fields: headline, narrative, primary_judgment, "
        "perspectives, trend_cards, and watchlist. primary_judgment must include confidence. "
        "Each trend card must include direction, time_horizon, and confidence. "
        "Include a primary judgment, and make the narrative explicitly reference 30d or 90d. "
        "Never mention BD, 猎头, 赏金, 认领, 客户开发, 岗位来源, or 岗位链接. "
        "Do not expose source fields such as canonical_url or source_name."
    )


def build_market_intelligence_user_prompt(signal_payload: dict) -> str:
    return (
        "Create a concise market intelligence report from this sanitized signal payload. "
        "Use the exact JSON schema requested by the system prompt.\n\n"
        f"{json.dumps(signal_payload, ensure_ascii=False, sort_keys=True)}"
    )


def generate_market_report(signal_payload: dict) -> dict:
    if not should_use_llm():
        return build_rule_market_report(signal_payload)

    content = request_structured_json(
        [
            {"role": "system", "content": build_market_intelligence_system_prompt()},
            {"role": "user", "content": build_market_intelligence_user_prompt(signal_payload)},
        ]
    )
    report = parse_market_intelligence_report(content)
    validate_market_intelligence_report(report, allowed_terms=_allowed_terms(signal_payload))
    return report


def parse_market_intelligence_report(content: str) -> dict:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MarketIntelligenceReportError("report must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise MarketIntelligenceReportError("report must be a JSON object")
    return payload


def validate_market_intelligence_report(payload: dict, *, allowed_terms: set[str]) -> None:
    if not isinstance(payload, dict):
        raise MarketIntelligenceReportError("report must be a JSON object")

    _reject_banned_phrases(payload)
    _require_str(payload, "headline")
    narrative = _require_str(payload, "narrative")
    if "30d" not in narrative and "90d" not in narrative:
        raise MarketIntelligenceReportError("narrative must include 30d or 90d")

    primary_judgment = _require_dict(payload, "primary_judgment")
    _require_str(primary_judgment, "claim")
    _require_str(primary_judgment, "why_it_matters")
    confidence = _require_str(primary_judgment, "confidence")
    if confidence not in CONFIDENCE_VALUES:
        raise MarketIntelligenceReportError("primary_judgment.confidence is invalid")

    perspectives = _require_list(payload, "perspectives")
    lenses = set()
    for item in perspectives:
        if not isinstance(item, dict):
            raise MarketIntelligenceReportError("perspectives must contain objects")
        lens = _require_str(item, "lens")
        lenses.add(lens)
        _require_str(item, "judgment")
        evidence = _require_str_list(item, "evidence")
        _validate_evidence_terms(evidence, allowed_terms)
    if not PERSPECTIVE_LENSES.issubset(lenses):
        raise MarketIntelligenceReportError("perspectives must include all required lenses")

    trend_cards = _require_list(payload, "trend_cards")
    if len(trend_cards) > 4:
        raise MarketIntelligenceReportError("trend_cards must contain at most 4 cards")
    for card in trend_cards:
        if not isinstance(card, dict):
            raise MarketIntelligenceReportError("trend_cards must contain objects")
        _require_str(card, "title")
        direction = _require_str(card, "direction")
        if direction not in TREND_DIRECTIONS:
            raise MarketIntelligenceReportError("trend card direction is invalid")
        time_horizon = _require_str(card, "time_horizon")
        if time_horizon not in TREND_TIME_HORIZONS:
            raise MarketIntelligenceReportError("trend card time_horizon is invalid")
        _require_str(card, "judgment")
        evidence = _require_str_list(card, "evidence")
        _validate_evidence_terms(evidence, allowed_terms)
        card_confidence = _require_str(card, "confidence")
        if card_confidence not in CONFIDENCE_VALUES:
            raise MarketIntelligenceReportError("trend card confidence is invalid")

    watchlist = _require_str_list(payload, "watchlist")
    if len(watchlist) > 3:
        raise MarketIntelligenceReportError("watchlist must contain at most 3 items")


def build_rule_market_report(signal_payload: dict) -> dict:
    headline = "Market demand remains selective"
    narrative = (
        "The 30d signal is not strong enough to call a broad surge, while the 90d view "
        "supports a cautious read of steady demand."
    )
    return {
        "headline": headline,
        "narrative": narrative,
        "primary_judgment": {
            "claim": "Demand appears steady, with limited evidence for a broad acceleration.",
            "why_it_matters": "A conservative read avoids overstating sparse or uneven signals.",
            "confidence": "low",
        },
        "perspectives": [
            {
                "lens": "industry",
                "judgment": "Industry movement looks steady rather than clearly accelerating.",
                "evidence": ["30d signal", "90d context"],
            },
            {
                "lens": "product_business",
                "judgment": "Product and business impact should be interpreted cautiously.",
                "evidence": ["Limited structured signal"],
            },
            {
                "lens": "organization_hiring",
                "judgment": "Hiring posture appears selective from the available signal.",
                "evidence": ["Conservative fallback report"],
            },
        ],
        "trend_cards": [
            {
                "title": "Selective demand",
                "direction": "stable",
                "time_horizon": "30d",
                "judgment": "The available signal supports a stable rather than rising read.",
                "evidence": ["30d signal", "90d context"],
                "confidence": "low",
            }
        ],
        "watchlist": ["30d signal", "90d context"],
    }


def _allowed_terms(signal_payload: dict) -> set[str]:
    terms: set[str] = set()
    representative_samples = signal_payload.get("representative_samples")
    if not isinstance(representative_samples, list):
        return terms

    for sample in representative_samples:
        if not isinstance(sample, dict):
            continue
        for field in ("company", "title", "domain"):
            value = sample.get(field)
            if isinstance(value, str) and value.strip():
                terms.add(value.strip())
    return terms


def _reject_banned_phrases(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for phrase in BANNED_PHRASES:
        if phrase in serialized:
            raise MarketIntelligenceReportError(f"report contains banned phrase: {phrase}")


def _validate_evidence_terms(evidence: list[str], allowed_terms: set[str]) -> None:
    if not allowed_terms:
        return

    normalized_terms = [term.lower() for term in allowed_terms]
    for item in evidence:
        normalized_item = item.lower()
        if not any(term in normalized_item for term in normalized_terms):
            raise MarketIntelligenceReportError("evidence must contain an allowed term")


def _require_dict(payload: dict, field: str) -> dict:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise MarketIntelligenceReportError(f"{field} must be an object")
    return value


def _require_list(payload: dict, field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise MarketIntelligenceReportError(f"{field} must be a list")
    return value


def _require_str(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MarketIntelligenceReportError(f"{field} must be a non-empty string")
    return value


def _require_str_list(payload: dict, field: str) -> list[str]:
    value = _require_list(payload, field)
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise MarketIntelligenceReportError(f"{field} must be a list of non-empty strings")
    return value
