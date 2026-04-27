import json
import re
from typing import Any

from app.services.llm_client import request_structured_json, should_use_llm


CONFIDENCE_VALUES = {"low", "medium", "high"}
PERSPECTIVE_LENSES = {"industry", "product_business", "organization_hiring"}
TREND_DIRECTIONS = {"rising", "cooling", "shifting", "stable", "emerging"}
TREND_TIME_HORIZONS = {"7d", "30d", "90d"}
BANNED_DIRECT_PHRASES = (
    "bd_entry",
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
BANNED_TOKEN_TERMS = ("source", "link", "bounty", "bounties", "claim", "claims", "claimed")
BANNED_RIGHT_HYPHEN_TOKEN_TERMS = {"source", "link"}
BANNED_LEFT_OR_RIGHT_HYPHEN_TOKEN_TERMS = {"bounty", "bounties", "claim", "claims", "claimed"}
THEME_TERM_ALIASES = {
    "AI infra": ("AI基础设施",),
    "agent / RAG": ("Agent/RAG", "agent/RAG"),
    "data platform": ("数据平台",),
    "Web3 infra": ("Web3基础设施",),
    "wallet / payment": ("钱包/支付",),
    "security": ("安全",),
    "risk / compliance": ("风险/合规",),
    "trading infra": ("交易基础设施",),
    "developer tools": ("开发者工具",),
    "enterprise AI integration": ("企业AI集成",),
    "other": ("其他",),
}


class MarketIntelligenceReportError(Exception):
    pass


def build_market_intelligence_system_prompt() -> str:
    return (
        "You write market intelligence reports from sanitized hiring signals. "
        "Return only a JSON object with fields: headline, narrative, primary_judgment, "
        "perspectives, trend_cards, and watchlist. "
        'Return exactly this JSON shape and field names: {"headline": "...", '
        '"narrative": "...", "primary_judgment": {"claim": "...", '
        '"why_it_matters": "...", "confidence": "low|medium|high"}, '
        '"perspectives": [{"lens": "industry|product_business|organization_hiring", '
        '"judgment": "...", "evidence": ["..."]}], '
        '"trend_cards": [{"title": "...", '
        '"direction": "rising|cooling|shifting|stable|emerging", '
        '"time_horizon": "7d|30d|90d", "judgment": "...", '
        '"evidence": ["..."], "confidence": "low|medium|high"}], '
        '"watchlist": ["..."]}. '
        "Do not use alternative keys such as statement, trend headline, or trend narrative. "
        "perspectives and trend_cards must be arrays, not objects. "
        "Required lenses are industry, product_business, and organization_hiring. "
        "Trend direction must be one of rising, cooling, shifting, stable, or emerging. "
        "Use watchlist max 3 and trend cards max 4. "
        "Write user-facing fields in Chinese. "
        "Evidence must quote or contain a representative sample company when present/title/domain. "
        "Every evidence item must contain a concrete company, title, domain, theme, "
        "function label, or count label from the input payload. "
        "Do not describe a job board or source site as a company or employer. "
        "Do not write generic evidence such as no specific title, no concrete role, "
        "or theme classification only. "
        "Include a primary judgment, and include at least one 30d or 90d trend card. "
        "BD or Business Development may appear only when it is literally a job function or market role. "
        "Never mention bounty, claim, claimed, 猎头, 赏金, 认领, 客户开发, 岗位来源, or 岗位链接. "
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

    allowed_terms = _allowed_terms(signal_payload)
    if not allowed_terms:
        return build_rule_market_report(signal_payload)

    content = request_structured_json(
        [
            {"role": "system", "content": build_market_intelligence_system_prompt()},
            {"role": "user", "content": build_market_intelligence_user_prompt(signal_payload)},
        ]
    )
    report = parse_market_intelligence_report(content)
    validate_market_intelligence_report(report, allowed_terms=allowed_terms)
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
    _require_str(payload, "narrative")

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
        evidence = _require_non_empty_str_list(item, "evidence")
        _validate_evidence_terms(evidence, allowed_terms)
    if not PERSPECTIVE_LENSES.issubset(lenses):
        raise MarketIntelligenceReportError("perspectives must include all required lenses")

    trend_cards = _require_list(payload, "trend_cards")
    if not 1 <= len(trend_cards) <= 4:
        raise MarketIntelligenceReportError("trend_cards must contain 1 to 4 cards")
    has_long_horizon_card = False
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
        if time_horizon in {"30d", "90d"}:
            has_long_horizon_card = True
        _require_str(card, "judgment")
        evidence = _require_non_empty_str_list(card, "evidence")
        _validate_evidence_terms(evidence, allowed_terms)
        card_confidence = _require_str(card, "confidence")
        if card_confidence not in CONFIDENCE_VALUES:
            raise MarketIntelligenceReportError("trend card confidence is invalid")
    if not has_long_horizon_card:
        raise MarketIntelligenceReportError("trend_cards must include a 30d or 90d card")

    watchlist = _require_str_list(payload, "watchlist")
    if len(watchlist) > 3:
        raise MarketIntelligenceReportError("watchlist must contain at most 3 items")


def build_rule_market_report(signal_payload: dict) -> dict:
    headline = "市场需求保持克制"
    narrative = (
        "近30天的信号还不足以判断行业进入普遍升温，90天视角更像是稳定需求中的局部调整。"
        "当前更适合看方向变化，而不是把短期波动解读成趋势反转。"
    )
    return {
        "headline": headline,
        "narrative": narrative,
        "primary_judgment": {
            "claim": "市场需求整体平稳，暂时没有足够证据支持大范围加速。",
            "why_it_matters": "这能避免把零散岗位波动误读成行业方向变化。",
            "confidence": "low",
        },
        "perspectives": [
            {
                "lens": "industry",
                "judgment": "行业层面更接近平稳运行，还看不出明显扩张。",
                "evidence": ["30d signal", "90d context"],
            },
            {
                "lens": "product_business",
                "judgment": "产品和商业方向的变化需要继续观察，现有信号不足以支撑强判断。",
                "evidence": ["Limited structured signal"],
            },
            {
                "lens": "organization_hiring",
                "judgment": "组织招聘更像选择性补强，而不是全面扩招。",
                "evidence": ["Conservative fallback report"],
            },
        ],
        "trend_cards": [
            {
                "title": "选择性需求",
                "direction": "stable",
                "time_horizon": "30d",
                "judgment": "现有信号更支持平稳判断，还不能判断为明显升温。",
                "evidence": ["30d signal", "90d context"],
                "confidence": "low",
            }
        ],
        "watchlist": ["30d signal", "90d context"],
    }


def _allowed_terms(signal_payload: dict) -> set[str]:
    terms: set[str] = set()
    representative_samples = signal_payload.get("representative_samples")
    if isinstance(representative_samples, list):
        for sample in representative_samples:
            if not isinstance(sample, dict):
                continue
            for field in ("company", "title", "domain"):
                value = sample.get(field)
                if isinstance(value, str) and value.strip():
                    _add_allowed_term(terms, value.strip())
                    if field == "title":
                        _add_title_alias_terms(terms, value.strip())
            seniority = sample.get("seniority")
            if isinstance(seniority, str) and seniority.strip():
                _add_allowed_term(terms, seniority.strip())

    windows = signal_payload.get("windows")
    if isinstance(windows, dict):
        for window in windows.values():
            if not isinstance(window, dict):
                continue
            for field in ("theme_counts", "function_counts"):
                counts = window.get(field)
                if not isinstance(counts, dict):
                    continue
                for value in counts:
                    if isinstance(value, str) and value.strip():
                        _add_allowed_term(terms, value.strip())
    return terms


def _add_allowed_term(terms: set[str], value: str) -> None:
    terms.add(value)
    for alias in THEME_TERM_ALIASES.get(value, ()):
        terms.add(alias)


def _add_title_alias_terms(terms: set[str], value: str) -> None:
    aliases = set()
    aliases.add(re.split(r"\s+[–—-]\s+", value, maxsplit=1)[0])
    compact = re.sub(r"^\[[^\]]+\]\s*", "", value)
    compact = re.sub(r"\s*\([^)]*\)", "", compact)
    compact = re.split(r"\s+[–—-]\s+", compact, maxsplit=1)[0]
    aliases.add(" ".join(compact.split()))

    for alias in aliases:
        if len(alias) >= 6:
            _add_allowed_term(terms, alias)


def _reject_banned_phrases(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    normalized = serialized.lower()
    for phrase in BANNED_DIRECT_PHRASES:
        if phrase.lower() in normalized:
            raise MarketIntelligenceReportError(f"report contains banned phrase: {phrase}")
    for text in _iter_token_check_texts(payload):
        normalized_text = text.lower()
        for term in BANNED_TOKEN_TERMS:
            if _contains_banned_token(normalized_text, term):
                raise MarketIntelligenceReportError(f"report contains banned phrase: {term}")


def _validate_evidence_terms(evidence: list[str], allowed_terms: set[str]) -> None:
    if not allowed_terms:
        return

    for item in evidence:
        if not any(_evidence_contains_term(item, term) for term in allowed_terms):
            raise MarketIntelligenceReportError("evidence must contain an allowed term")


def _evidence_contains_term(evidence: str, term: str) -> bool:
    normalized_term = _normalize_evidence_match_text(term)
    normalized_evidence = _normalize_evidence_match_text(evidence)
    if re.fullmatch(r"[a-z0-9]{1,3}", normalized_term):
        return _contains_ascii_token(normalized_evidence, normalized_term)
    return normalized_term in normalized_evidence


def _normalize_evidence_match_text(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _iter_token_check_texts(value: Any):
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key != "claim":
                yield key
            yield from _iter_token_check_texts(item)
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_token_check_texts(item)


def _contains_ascii_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9-]){re.escape(token)}(?![a-z0-9-])", text) is not None


def _contains_banned_token(text: str, token: str) -> bool:
    if token in BANNED_LEFT_OR_RIGHT_HYPHEN_TOKEN_TERMS:
        return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text) is not None
    if token in BANNED_RIGHT_HYPHEN_TOKEN_TERMS:
        return re.search(rf"(?<![a-z0-9-]){re.escape(token)}(?![a-z0-9])", text) is not None
    return _contains_ascii_token(text, token)


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


def _require_non_empty_str_list(payload: dict, field: str) -> list[str]:
    value = _require_str_list(payload, field)
    if not value:
        raise MarketIntelligenceReportError(f"{field} must be a non-empty list")
    return value
