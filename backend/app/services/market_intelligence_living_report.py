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
LIVING_REPORT_LLM_TIMEOUT_SECONDS = 120
MIN_EXECUTIVE_SUMMARY_CHARS = 120
MIN_SECTION_BODY_CHARS = 180
MIN_TOTAL_REPORT_CHARS = 1800


class LivingMarketReportError(Exception):
    pass


def build_living_market_report_system_prompt(input_payload: dict | None = None) -> str:
    if _report_language(input_payload) == "ja-JP":
        return (
            "You generate a Japanese Living Market Report from sanitized recruiting facts. "
            "Return only a JSON object, no Markdown. "
            "本文、headline、executive_summary、section title/body、claim、watchlist、change_reason は日本語で書く。"
            "Company names, job titles, AI/Web3/JD/RootData/DevRel, and source terms may remain in their original language. "
            "目標は日本語で 2000-3000 文字。日報、ランキング、求人の羅列にしない。"
            "Even when mode is incremental_update, output a complete market analysis report, not a patch or changelog. "
            "Each section must compare 7d/30d/90d/180d and explain structure, changes, causes, and uncertainty. "
            "Follow input JSON report_scope: market_scope and data_source_scope define the boundary; narrative_rules control title and framing. "
            "If japan_recruiting_profile is present, use it as the primary analysis frame: functions, experience, language, location, remote policy, employment type, salary disclosure, and source mix. "
            "Treat market_theme/theme_counts and industry_hint_counts as secondary context, not the report backbone. "
            "If report_scope.not_a_vertical_web3_report is true, Web3/Crypto/Blockchain is only a segment signal; do not put it in the headline unless the input statistics show a clear sample majority. "
            "Use only statistics and evidence_id from input JSON; every claim must include evidence_ids. "
            "Do not add external facts. Do not output canonical_url/source_name/job_url/full_description, 猎头, 赏金, 認領, クライアント開拓, 求人ソース, 求人リンク. "
            "Fields must strictly match the living_market_report schema. Do not output date, statement, or any unknown schema fields. "
            "The claim text field must be named claim. status must be new/reinforced/weakened/retired."
            "\n\nReturn exactly this structure:"
            "{"
            '"kind":"living_market_report",'
            '"schema_version":"living-market-report-v1",'
            '"headline":"日本語タイトル",'
            '"version":1,'
            '"mode":"baseline_seed or incremental_update",'
            '"previous_snapshot_id":null,'
            '"seed_window_days":180,'
            '"generated_at":"ISO time",'
            '"executive_summary":"日本語の要約",'
            '"sections":[{"section_id":"market_structure","title":"市場構造","body":"分析本文","claim_ids":["c1"]}],'
            '"claims":[{"claim_id":"c1","previous_claim_id":null,"status":"new","claim":"判断","confidence":"low","evidence_ids":["fact-1"],"evidence_notes":["証拠メモ"],"change_reason":"変化理由"}],'
            '"watchlist":[{"topic":"観察テーマ","why_watch":"見る理由","evidence_ids":["fact-1"]}],'
            '"data_quality":{}'
            "}。"
            "sections must contain 3-5 items and section_id must be market_structure/demand_shifts/company_patterns/risk_and_uncertainty; "
            "claims must contain 4-10 items; each claim uses 1-5 existing input evidence_id values. "
            "executive_summary must be at least 120 Japanese characters; each section.body must be at least 180 Japanese characters."
        )
    return (
        "你从脱敏招聘事实生成中文 Living Market Report，只返回 JSON object，不要 Markdown。"
        "目标 2000-3000 个中文字符，不写日报、不写榜单、不写岗位流水账。"
        "即使 mode 是 incremental_update，也必须输出一份完整市场分析报告，不是上一版的补丁、摘要或更新日志。"
        "每个 section 都要展开数据变化、原因解释和不确定性，必须对比 7d/30d/90d/180d。"
        "必须遵守输入 JSON 的 report_scope：按 market_scope 和 data_source_scope 定义报告边界，按 narrative_rules 控制标题和总论。"
        "如果 report_scope.not_a_vertical_web3_report 为 true，Web3/Crypto/Blockchain 只能作为细分信号；除非输入统计显示该类样本明确过半，不得写进 headline。"
        "只能使用输入 JSON 中的统计和 evidence_id；每个 claim 必须有 evidence_ids。"
        "禁止补外部事实，禁止输出 canonical_url/source_name/job_url/full_description、猎头、赏金、认领、客户开发、岗位来源、岗位链接。"
        "字段必须严格匹配 living_market_report schema，不能输出 date、statement 或任何 schema 外字段。"
        "claim 文本字段必须叫 claim，不能叫 statement。status 只能是 new/reinforced/weakened/retired。"
        "\n\n必须返回这个结构："
        "{"
        '"kind":"living_market_report",'
        '"schema_version":"living-market-report-v1",'
        '"headline":"中文标题",'
        '"version":1,'
        '"mode":"baseline_seed 或 incremental_update",'
        '"previous_snapshot_id":null,'
        '"seed_window_days":180,'
        '"generated_at":"ISO 时间",'
        '"executive_summary":"核心判断摘要",'
        '"sections":[{"section_id":"market_structure","title":"市场结构","body":"分析正文","claim_ids":["c1"]}],'
        '"claims":[{"claim_id":"c1","previous_claim_id":null,"status":"new","claim":"判断","confidence":"low","evidence_ids":["fact-1"],"evidence_notes":["证据说明"],"change_reason":"变化原因"}],'
        '"watchlist":[{"topic":"观察主题","why_watch":"为什么要看","evidence_ids":["fact-1"]}],'
        '"data_quality":{}'
        "}。"
        "sections 必须 3-5 个，section_id 只能是 market_structure/demand_shifts/company_patterns/risk_and_uncertainty；"
        "claims 必须 4-10 个；每个 claim 使用 1-5 个输入中存在的 evidence_id。"
        "executive_summary 至少 120 个中文字符；每个 section.body 至少 180 个中文字符。"
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
        raise LivingMarketReportError("LLM is disabled or missing API key")

    messages = [
        {"role": "system", "content": build_living_market_report_system_prompt(input_payload)},
        {"role": "user", "content": build_living_market_report_user_prompt(input_payload)},
    ]
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            content = request_structured_json(messages, timeout_seconds=LIVING_REPORT_LLM_TIMEOUT_SECONDS)
            report = parse_market_intelligence_report(content)
            report["version"] = version
            report["mode"] = mode
            report["previous_snapshot_id"] = previous_snapshot_id
            report["seed_window_days"] = 180
            report["generated_at"] = generated_at.replace(microsecond=0).isoformat()
            validate_living_market_report(report, input_payload=input_payload, expected_version=version)
            quality_warnings = _quality_warnings(report)
            if quality_warnings and attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上次输出太短，不能作为完整 Living Market Report。"
                            f"问题：{'; '.join(quality_warnings)}。"
                            "请扩写 executive_summary 和每个 section.body。"
                            "保持相同 JSON schema，只使用输入证据，不添加外部事实，不要解释。"
                        ),
                    }
                )
                continue
            return report
        except Exception as exc:
            last_error = exc
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"上次输出未通过校验：{str(exc)[:300]}。"
                        "重新输出完整 JSON object，不要解释。"
                        "只修 JSON/schema，不添加输入外事实。"
                        "不要输出 date、statement 或 schema 外字段；claim 文本字段必须叫 claim。"
                    ),
                }
            )
            if attempt == 0:
                continue
    raise LivingMarketReportError(f"LLM report failed validation after retries: {str(last_error)[:300]}")


def _quality_warnings(payload: dict) -> list[str]:
    warnings: list[str] = []
    executive_summary = payload.get("executive_summary")
    if isinstance(executive_summary, str) and len(executive_summary.strip()) < MIN_EXECUTIVE_SUMMARY_CHARS:
        warnings.append("executive_summary 太短")

    sections = payload.get("sections")
    if isinstance(sections, list):
        short_sections = [
            section.get("section_id") or section.get("title") or "unknown"
            for section in sections
            if isinstance(section, dict) and len(str(section.get("body") or "").strip()) < MIN_SECTION_BODY_CHARS
        ]
        if short_sections:
            warnings.append(f"section.body 太短: {', '.join(str(item) for item in short_sections[:4])}")

    if _report_text_length(payload) < MIN_TOTAL_REPORT_CHARS:
        warnings.append("整篇报告正文太短")
    return warnings


def _report_text_length(payload: dict) -> int:
    text_parts = [str(payload.get("headline") or ""), str(payload.get("executive_summary") or "")]
    sections = payload.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict):
                text_parts.append(str(section.get("title") or ""))
                text_parts.append(str(section.get("body") or ""))
    claims = payload.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict):
                text_parts.append(str(claim.get("claim") or ""))
                text_parts.append(str(claim.get("change_reason") or ""))
    return len("".join(text_parts).strip())


def validate_living_market_report(payload: dict, *, input_payload: dict, expected_version: int) -> None:
    if not isinstance(payload, dict):
        raise LivingMarketReportError("report must be a JSON object")
    extra = set(payload) - TOP_LEVEL_FIELDS
    if extra:
        raise LivingMarketReportError(f"unknown fields: {sorted(extra)}")
    _reject_leakage(payload)
    _validate_report_scope(payload, input_payload=input_payload)
    if payload.get("kind") != KIND:
        raise LivingMarketReportError("kind is invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise LivingMarketReportError("schema_version is invalid")
    _str(payload, "headline")
    if payload.get("version") != expected_version:
        raise LivingMarketReportError("version is invalid")
    if expected_version == 1 and not _has_180d_window(input_payload):
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


def _validate_report_scope(payload: dict, *, input_payload: dict) -> None:
    report_scope = input_payload.get("report_scope")
    if not isinstance(report_scope, dict) or report_scope.get("not_a_vertical_web3_report") is not True:
        return
    headline = payload.get("headline")
    if not isinstance(headline, str) or not _mentions_web3_vertical(headline):
        return
    if _web3_sample_share(input_payload) <= float(report_scope.get("web3_headline_requires_sample_share_gt") or 0.5):
        raise LivingMarketReportError("Web3/Crypto/Blockchain headline requires Web3 sample majority for this report scope")


def _has_180d_window(input_payload: dict) -> bool:
    market_windows = input_payload.get("market_windows")
    if isinstance(market_windows, dict) and "180d" in market_windows:
        return True
    recruiting_profile = input_payload.get("japan_recruiting_profile")
    if isinstance(recruiting_profile, dict):
        windows = recruiting_profile.get("windows")
        return isinstance(windows, dict) and "180d" in windows
    return False


def _mentions_web3_vertical(text: str) -> bool:
    return bool(re.search(r"web3|crypto|blockchain|区块链|加密|暗号資産|仮想通貨", text, re.IGNORECASE))


def _web3_sample_share(input_payload: dict) -> float:
    market_windows = input_payload.get("market_windows")
    if not isinstance(market_windows, dict):
        return 0.0
    window_180d = market_windows.get("180d")
    if not isinstance(window_180d, dict):
        return 0.0
    job_count = window_180d.get("job_count")
    if not isinstance(job_count, int) or job_count <= 0:
        return 0.0
    theme_counts = window_180d.get("theme_counts")
    if not isinstance(theme_counts, dict):
        return 0.0
    web3_count = 0
    for theme, count in theme_counts.items():
        if isinstance(theme, str) and _mentions_web3_vertical(theme) and isinstance(count, int):
            web3_count += count
    return web3_count / job_count


def build_rule_living_market_report(
    input_payload: dict,
    *,
    version: int,
    mode: str,
    previous_snapshot_id: int | None,
    generated_at: datetime,
) -> dict:
    if _report_language(input_payload) == "ja-JP":
        return _build_japanese_rule_living_market_report(
            input_payload,
            version=version,
            mode=mode,
            previous_snapshot_id=previous_snapshot_id,
            generated_at=generated_at,
        )
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


def _build_japanese_rule_living_market_report(
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
        "headline": "市場需要は慎重に推移",
        "version": version,
        "mode": mode,
        "previous_snapshot_id": previous_snapshot_id,
        "seed_window_days": 180,
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "executive_summary": "日本の公開求人サンプルでは、構造的な需要は見えるものの、市場全体が一気に加速しているとまでは言えません。",
        "sections": [
            {
                "section_id": "market_structure",
                "title": "市場構造",
                "body": "市場構造は、可視化されたテーマが安定して現れるかどうかを軸に見る必要があります。短期の増減だけで日本市場全体の拡大と判断するのはまだ早く、職種とテーマの組み合わせを継続して確認する段階です。",
                "claim_ids": ["c1"],
            },
            {
                "section_id": "demand_shifts",
                "title": "需要変化",
                "body": "短期ウィンドウの変化は 180 日の基線に戻して読む必要があります。現時点では方向感を把握する材料にはなりますが、強いトレンドとして断定するには追加サンプルが必要です。",
                "claim_ids": ["c2"],
            },
            {
                "section_id": "company_patterns",
                "title": "企業と組織シグナル",
                "body": "代表サンプルからは、企業の採用が全面的な拡大というより選択的な補強に近いことが読み取れます。特定職能の継続的な出現があるかを見続ける必要があります。",
                "claim_ids": ["c3"],
            },
            {
                "section_id": "risk_and_uncertainty",
                "title": "不確実性",
                "body": "このレポートは構造化された公開求人サンプルに基づくため、日本市場の完全な履歴や全体規模を示すものではありません。サンプル数、投稿日、取得日の偏りを前提に読む必要があります。",
                "claim_ids": ["c4"],
            },
        ],
        "claims": [
            _japanese_rule_claim("c1", "構造的な需要は見えるが、証拠強度は慎重に扱うべきです。", evidence_id),
            _japanese_rule_claim("c2", "短期変化だけでは市場全体の加速を示すには不十分です。", evidence_id),
            _japanese_rule_claim("c3", "組織シグナルは選択的な補強に近い状態です。", evidence_id),
            _japanese_rule_claim("c4", "サンプル品質の制約を継続して明示する必要があります。", evidence_id),
        ],
        "watchlist": [{"topic": "構造的テーマ", "why_watch": "今後の短期ウィンドウで継続的に広がるかを確認します。", "evidence_ids": [evidence_id]}],
        "data_quality": data_quality,
    }


def _japanese_rule_claim(claim_id: str, claim: str, evidence_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "previous_claim_id": None,
        "status": "new",
        "claim": claim,
        "confidence": "low",
        "evidence_ids": [evidence_id],
        "evidence_notes": ["ルール fallback は入力内の構造化証拠を使用します。"],
        "change_reason": "LLM が利用できない、または出力が検証を通過しなかったため、保守的なルールレポートを使用します。",
    }


def _report_language(input_payload: dict | None) -> str:
    report_task = input_payload.get("report_task") if isinstance(input_payload, dict) else None
    if isinstance(report_task, dict) and report_task.get("language") == "ja-JP":
        return "ja-JP"
    if isinstance(input_payload, dict) and input_payload.get("region") == "japan":
        return "ja-JP"
    return "zh-CN"


def _allowed_evidence_ids(input_payload: dict) -> set[str]:
    evidence_ids: set[str] = set()
    for field in ("new_facts", "representative_samples"):
        value = input_payload.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str):
                    evidence_ids.add(item["evidence_id"])

    allowed_terms = input_payload.get("allowed_evidence_terms")
    if isinstance(allowed_terms, list):
        for term in allowed_terms:
            if isinstance(term, str) and _looks_like_evidence_id(term):
                evidence_ids.add(term)

    previous_report = input_payload.get("previous_report")
    if isinstance(previous_report, dict):
        claims = previous_report.get("active_claims")
        if isinstance(claims, list):
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                for evidence_id in claim.get("evidence_ids") or []:
                    if isinstance(evidence_id, str) and _looks_like_evidence_id(evidence_id):
                        evidence_ids.add(evidence_id)
    return evidence_ids


def _looks_like_evidence_id(value: str) -> bool:
    return bool(re.fullmatch(r"(fact-[a-zA-Z0-9]+|e\d+)", value.strip()))


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
