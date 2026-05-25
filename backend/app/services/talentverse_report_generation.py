import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot, TalentverseReport
from app.services.llm_client import request_structured_json
from app.services.region import GLOBAL_REGION

TALENTVERSE_REPORT_STATUS_DRAFT = "draft"
TALENTVERSE_REPORT_STATUS_PUBLISHED = "published"
TALENTVERSE_REPORT_STATUS_FAILED = "failed"
TALENTVERSE_LOCALE = "zh-CN"
TALENTVERSE_SOURCE_NAME = "Talent Signal"
TALENTVERSE_SOURCE_URL = "https://talentsignal.cloud"
TALENTVERSE_CATEGORY = "market-intelligence"
TALENTVERSE_TAGS = ["global", "talent-strategy", "ai", "data"]
TALENTVERSE_LLM_TIMEOUT_SECONDS = 120
DB_CREDENTIAL_URL_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@[^\s]+",
    re.IGNORECASE,
)
OPENAI_KEY_PATTERN = re.compile(r"sk-[^\s,;]+", re.IGNORECASE)
KEY_VALUE_SECRET_PATTERN = re.compile(
    r"\b([a-z0-9_]*(?:api_key|token|password))\s*([=:])\s*([^\s,;]+)",
    re.IGNORECASE,
)
AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\bAuthorization\s*:\s*Bearer\s+[^\s,;]+",
    re.IGNORECASE,
)
FORBIDDEN_FIELDS = {
    "canonical_url",
    "source_name",
    "source_url",
    "job_url",
    "full_description",
    "bounty_grade",
    "claimed_names",
    "claim_status",
    "bd_entry",
    "signal_tags",
}
FORBIDDEN_TEXT = (
    "招聘中介",
    "简历推荐",
    "海量人才库",
    "精准匹配",
    "AI-powered headhunter",
    "传统猎头",
    "全球领先",
    "赋能企业",
    "生态闭环",
    "一站式解决方案",
    "canonical_url",
    "source_name",
    "full_description",
    "job_url",
)


class TalentverseReportError(Exception):
    pass


def sanitize_talentverse_error(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    message = DB_CREDENTIAL_URL_PATTERN.sub("[redacted]", message)
    message = AUTHORIZATION_BEARER_PATTERN.sub("Authorization: Bearer [redacted]", message)
    message = OPENAI_KEY_PATTERN.sub("[redacted]", message)
    return KEY_VALUE_SECRET_PATTERN.sub(_redact_key_value_secret, message)


def build_talentverse_slug(snapshot: MarketIntelligenceSnapshot) -> str:
    living_report = _living_report(snapshot)
    version = living_report.get("version")
    if not isinstance(version, int):
        raise TalentverseReportError("living_report.version must be an integer")
    return f"{snapshot.region}-talentverse-report-{snapshot.snapshot_date.isoformat()}-v{version}"


def generate_talentverse_report_for_snapshot(db: Session, *, raw_snapshot_id: int) -> dict[str, Any]:
    snapshot = db.get(MarketIntelligenceSnapshot, raw_snapshot_id)
    if snapshot is None:
        return {"status": "skipped", "reason": "raw_report_missing"}
    if snapshot.region != GLOBAL_REGION:
        return {"status": "skipped", "reason": "unsupported_region"}
    if snapshot.status != "success":
        return {"status": "skipped", "reason": "raw_report_not_success"}

    try:
        existing = _load_existing_report(db, raw_report_id=snapshot.id)
        if existing is not None and existing.status == TALENTVERSE_REPORT_STATUS_PUBLISHED:
            return {"status": "published", "report_id": existing.id, "slug": existing.slug}

        slug = build_talentverse_slug(snapshot)
        now = snapshot.generated_at.replace(microsecond=0)
        content = request_structured_json(
            [
                {"role": "system", "content": build_talentverse_system_prompt()},
                {"role": "user", "content": build_talentverse_user_prompt(snapshot)},
            ],
            timeout_seconds=TALENTVERSE_LLM_TIMEOUT_SECONDS,
        )
        payload = parse_talentverse_payload(content)
        validate_talentverse_payload(payload, raw_snapshot=snapshot)
        final_payload = normalize_talentverse_payload(payload, raw_snapshot=snapshot, slug=slug)
        report = _upsert_report(
            db,
            existing=existing,
            snapshot=snapshot,
            slug=slug,
            status=TALENTVERSE_REPORT_STATUS_PUBLISHED,
            payload=final_payload,
            error_message=None,
            published_at=now,
        )
        return {"status": "published", "report_id": report.id, "slug": report.slug}
    except Exception as exc:  # noqa: BLE001
        error_message = sanitize_talentverse_error(exc)
        try:
            report = _record_failed_report(db, snapshot=snapshot, error_message=error_message)
        except Exception as record_exc:  # noqa: BLE001
            db.rollback()
            return {
                "status": "failed",
                "error": error_message,
                "record_error": sanitize_talentverse_error(record_exc),
            }
        return {"status": "failed", "report_id": report.id, "error": error_message}


def build_talentverse_system_prompt() -> str:
    return (
        "You transform a sanitized Talent Signal living market report into a Talentverse website research report. "
        "Return only one JSON object. Do not return Markdown or HTML. "
        "Talentverse is an AI-native talent intelligence and executive recruiting firm helping frontier technology "
        "and new economy companies identify, evaluate, and hire mission-critical talent. "
        "Write in natural Chinese. Use phrases such as AI 原生人才战略, 人才判断, 人才研究, 高确定性招聘, 关键岗位, "
        "前沿科技招聘, 技术与产品人才, 新经济团队. "
        "Do not use 招聘中介, 简历推荐, 海量人才库, 精准匹配, AI-powered headhunter, 传统猎头, 全球领先, "
        "赋能企业, 生态闭环, 一站式解决方案. "
        "Preserve key numbers, time windows, facts, confidence labels, and evidence references from the input. "
        "Do not invent data. Every important judgment must include hiringImplication. "
        "Do not expose raw job links, full JD, source_name, canonical_url, full_description, job_url, or similar fields. "
        "Generate fields exactly matching this schema: title, subtitle, executiveSummary, keySignals, marketStructure, "
        "demandShift, talentStrategyImplications, risksAndWatchlist, talentverseView, methodologyNote, faq, "
        "glossaryTerms, evidenceRefs, seo. "
        "keySignals items require signal, data, interpretation, hiringImplication, confidence, evidenceRefs. "
        "marketStructure and demandShift require body and metrics. "
        "talentStrategyImplications require title and body. "
        "risksAndWatchlist require topic, reason, evidenceRefs. "
        "methodologyNote requires sampleCount, windowDays, body. "
        "faq requires question and answer. glossaryTerms require term and definition. "
        "evidenceRefs require id, note, confidence. seo requires title, description, keywords. "
        "The report must be useful for SEO, GEO, and AI citation: include stable definitions, clear claims, and evidence IDs."
    )


def build_talentverse_user_prompt(snapshot: MarketIntelligenceSnapshot) -> str:
    living_report = _living_report(snapshot)
    input_payload = {
        "rawReportId": f"market-intelligence-snapshot-{snapshot.id}",
        "region": snapshot.region,
        "locale": TALENTVERSE_LOCALE,
        "snapshotDate": snapshot.snapshot_date.isoformat(),
        "generatedAt": snapshot.generated_at.replace(microsecond=0).isoformat(),
        "windowDays": snapshot.window_days,
        "source": {
            "name": TALENTVERSE_SOURCE_NAME,
            "url": TALENTVERSE_SOURCE_URL,
            "generatedAt": snapshot.generated_at.replace(microsecond=0).isoformat(),
            "version": living_report.get("version"),
        },
        "livingReport": living_report,
        "dataQuality": living_report.get("data_quality"),
    }
    return json.dumps(input_payload, ensure_ascii=False, sort_keys=True)


def parse_talentverse_payload(content: str) -> dict:
    try:
        payload = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise TalentverseReportError("talentverse response must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise TalentverseReportError("talentverse response must be a JSON object")
    return payload


def validate_talentverse_payload(payload: dict, *, raw_snapshot: MarketIntelligenceSnapshot) -> None:
    required_fields = {
        "title",
        "subtitle",
        "executiveSummary",
        "keySignals",
        "marketStructure",
        "demandShift",
        "talentStrategyImplications",
        "risksAndWatchlist",
        "talentverseView",
        "methodologyNote",
        "faq",
        "glossaryTerms",
        "evidenceRefs",
        "seo",
    }
    missing = sorted(required_fields - payload.keys())
    if missing:
        raise TalentverseReportError(f"missing required fields: {', '.join(missing)}")
    _reject_forbidden_fields(payload)
    _reject_forbidden_text(payload)
    _require_non_empty_text(payload, "title")
    _require_non_empty_text(payload, "subtitle")
    _require_non_empty_text(payload, "executiveSummary")
    _require_non_empty_list(payload, "keySignals")
    _validate_key_signal_items(payload["keySignals"])
    _validate_section_object(payload.get("marketStructure"), field="marketStructure")
    _validate_section_object(payload.get("demandShift"), field="demandShift")
    _require_non_empty_list(payload, "talentStrategyImplications")
    _validate_text_object_items(
        payload["talentStrategyImplications"],
        field="talentStrategyImplications",
        required_text_fields=("title", "body"),
    )
    _require_non_empty_list(payload, "risksAndWatchlist")
    _validate_text_object_items(
        payload["risksAndWatchlist"],
        field="risksAndWatchlist",
        required_text_fields=("topic", "reason"),
        optional_list_fields=("evidenceRefs",),
    )
    _require_non_empty_text(payload, "talentverseView")
    _require_non_empty_list(payload, "faq")
    _validate_text_object_items(payload["faq"], field="faq", required_text_fields=("question", "answer"))
    _require_non_empty_list(payload, "glossaryTerms")
    _validate_text_object_items(payload["glossaryTerms"], field="glossaryTerms", required_text_fields=("term", "definition"))
    _require_non_empty_list(payload, "evidenceRefs")
    _validate_text_object_items(payload["evidenceRefs"], field="evidenceRefs", required_text_fields=("id", "note", "confidence"))
    methodology = payload.get("methodologyNote")
    if not isinstance(methodology, dict):
        raise TalentverseReportError("methodologyNote must be an object")
    if methodology.get("sampleCount") is None:
        raise TalentverseReportError("methodologyNote.sampleCount is required")
    if methodology.get("windowDays") != raw_snapshot.window_days:
        raise TalentverseReportError("methodologyNote.windowDays must match raw snapshot")
    _require_non_empty_text(methodology, "body")
    seo = payload.get("seo")
    if not isinstance(seo, dict):
        raise TalentverseReportError("seo must be an object")
    _require_non_empty_text(seo, "title")
    _require_non_empty_text(seo, "description")
    if not isinstance(seo.get("keywords"), list) or not seo["keywords"]:
        raise TalentverseReportError("seo.keywords must be a non-empty list")


def normalize_talentverse_payload(payload: dict, *, raw_snapshot: MarketIntelligenceSnapshot, slug: str) -> dict:
    living_report = _living_report(raw_snapshot)
    generated_at = raw_snapshot.generated_at.replace(microsecond=0).isoformat()
    version = living_report["version"]
    return {
        "id": None,
        "rawReportId": f"market-intelligence-snapshot-{raw_snapshot.id}",
        "slug": slug,
        "region": raw_snapshot.region,
        "locale": TALENTVERSE_LOCALE,
        "title": payload["title"].strip(),
        "subtitle": payload["subtitle"].strip(),
        "executiveSummary": payload["executiveSummary"].strip(),
        "keySignals": payload["keySignals"],
        "marketStructure": payload["marketStructure"],
        "demandShift": payload["demandShift"],
        "talentStrategyImplications": payload["talentStrategyImplications"],
        "risksAndWatchlist": payload["risksAndWatchlist"],
        "talentverseView": payload["talentverseView"].strip(),
        "methodologyNote": payload["methodologyNote"],
        "faq": payload["faq"],
        "glossaryTerms": payload["glossaryTerms"],
        "evidenceRefs": payload["evidenceRefs"],
        "source": {
            "name": TALENTVERSE_SOURCE_NAME,
            "url": TALENTVERSE_SOURCE_URL,
            "generatedAt": generated_at,
            "version": version,
        },
        "seo": payload["seo"],
        "status": TALENTVERSE_REPORT_STATUS_PUBLISHED,
        "publishedAt": generated_at,
        "updatedAt": generated_at,
        "version": version,
        "category": TALENTVERSE_CATEGORY,
        "tags": TALENTVERSE_TAGS,
    }


def _redact_key_value_secret(match: re.Match) -> str:
    separator = match.group(2)
    if separator == ":":
        return f"{match.group(1)}: [redacted]"
    return f"{match.group(1)}=[redacted]"


def _upsert_report(
    db: Session,
    *,
    existing: TalentverseReport | None,
    snapshot: MarketIntelligenceSnapshot,
    slug: str,
    status: str,
    payload: dict,
    error_message: str | None,
    published_at: datetime | None,
) -> TalentverseReport:
    living_report = _safe_living_report(snapshot)
    now = snapshot.generated_at.replace(microsecond=0)
    report = existing or TalentverseReport(raw_report_id=snapshot.id, created_at=now)
    report.slug = slug
    report.region = snapshot.region
    report.locale = TALENTVERSE_LOCALE
    report.title = payload.get("title") or living_report.get("headline") or "Talentverse Report"
    report.status = status
    report.published_at = published_at
    report.updated_at = now
    report.version = _safe_living_version(snapshot)
    report.payload = payload
    report.error_message = error_message
    db.add(report)
    db.commit()
    db.refresh(report)
    if report.payload and report.payload.get("id") is None:
        report.payload = {**report.payload, "id": f"tv-report-{report.id}"}
        db.add(report)
        db.commit()
        db.refresh(report)
    return report


def _record_failed_report(db: Session, *, snapshot: MarketIntelligenceSnapshot, error_message: str) -> TalentverseReport:
    existing = _load_existing_report(db, raw_report_id=snapshot.id)
    return _upsert_report(
        db,
        existing=existing,
        snapshot=snapshot,
        slug=_safe_slug(snapshot),
        status=TALENTVERSE_REPORT_STATUS_FAILED,
        payload={},
        error_message=error_message,
        published_at=None,
    )


def _load_existing_report(db: Session, *, raw_report_id: int) -> TalentverseReport | None:
    return db.execute(
        select(TalentverseReport).where(TalentverseReport.raw_report_id == raw_report_id)
    ).scalar_one_or_none()


def _safe_slug(snapshot: MarketIntelligenceSnapshot) -> str:
    try:
        return build_talentverse_slug(snapshot)
    except TalentverseReportError:
        return f"{snapshot.region}-talentverse-report-{snapshot.snapshot_date.isoformat()}-raw-{snapshot.id}-failed"


def _safe_living_report(snapshot: MarketIntelligenceSnapshot) -> dict:
    try:
        return _living_report(snapshot)
    except TalentverseReportError:
        return {}


def _safe_living_version(snapshot: MarketIntelligenceSnapshot) -> int:
    living_report = _safe_living_report(snapshot)
    version = living_report.get("version")
    return version if isinstance(version, int) else 0


def _living_report(snapshot: MarketIntelligenceSnapshot) -> dict:
    report_payload = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
    living_report = report_payload.get("living_report")
    if not isinstance(living_report, dict):
        raise TalentverseReportError("raw snapshot is missing living_report")
    if living_report.get("kind") != "living_market_report":
        raise TalentverseReportError("raw living_report kind is unsupported")
    return living_report


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return match.group(1).strip() if match else stripped


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_FIELDS:
                raise TalentverseReportError(f"forbidden field: {key}")
            _reject_forbidden_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_fields(item)


def _reject_forbidden_text(value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False)
    for token in FORBIDDEN_TEXT:
        if token in text:
            raise TalentverseReportError(f"forbidden text: {token}")


def _require_non_empty_text(payload: dict, field: str) -> None:
    if not isinstance(payload.get(field), str) or not payload[field].strip():
        raise TalentverseReportError(f"{field} must be non-empty text")


def _require_non_empty_list(payload: dict, field: str) -> None:
    if not isinstance(payload.get(field), list) or not payload[field]:
        raise TalentverseReportError(f"{field} must be a non-empty list")


def _validate_key_signal_items(items: list) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TalentverseReportError(f"keySignals[{index}] must be an object")
        for field in ("signal", "data", "interpretation", "hiringImplication", "confidence"):
            _require_non_empty_text(item, field)
        evidence_refs = item.get("evidenceRefs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise TalentverseReportError(f"keySignals[{index}].evidenceRefs must be a non-empty list")


def _validate_section_object(value: object, *, field: str) -> None:
    if not isinstance(value, dict):
        raise TalentverseReportError(f"{field} must be an object")
    _require_non_empty_text(value, "body")
    metrics = value.get("metrics")
    if not isinstance(metrics, list):
        raise TalentverseReportError(f"{field}.metrics must be a list")
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            raise TalentverseReportError(f"{field}.metrics[{index}] must be an object")
        for metric_field in ("label", "value", "description"):
            _require_non_empty_text(metric, metric_field)


def _validate_text_object_items(
    items: list,
    *,
    field: str,
    required_text_fields: tuple[str, ...],
    optional_list_fields: tuple[str, ...] = (),
) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TalentverseReportError(f"{field}[{index}] must be an object")
        for required_field in required_text_fields:
            _require_non_empty_text(item, required_field)
        for list_field in optional_list_fields:
            if list_field in item and not isinstance(item[list_field], list):
                raise TalentverseReportError(f"{field}[{index}].{list_field} must be a list")
