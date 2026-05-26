from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TalentverseReport

PUBLISHED_STATUS = "published"
DEFAULT_LOCALE = "zh-CN"
MAX_LIMIT = 100


class TalentverseCursorError(ValueError):
    pass


def list_published_talentverse_reports(
    db: Session,
    *,
    region: str | None = None,
    locale: str | None = None,
    status: str = PUBLISHED_STATUS,
    limit: int = 20,
    cursor: str | None = None,
    updated_after: datetime | None = None,
) -> dict:
    normalized_limit = _normalize_limit(limit)
    if status != PUBLISHED_STATUS:
        return {"items": [], "pageInfo": {"limit": normalized_limit, "nextCursor": None}}

    query = select(TalentverseReport).where(TalentverseReport.status == PUBLISHED_STATUS)
    if region:
        query = query.where(TalentverseReport.region == region)
    if updated_after is not None:
        query = query.where(TalentverseReport.updated_at > updated_after)
    requested_locale = locale or DEFAULT_LOCALE
    matches: list[tuple[TalentverseReport, dict]] = []
    next_query_cursor = cursor
    batch_size = max(normalized_limit + 1, 20)

    while len(matches) <= normalized_limit:
        batch_query = query
        if next_query_cursor:
            cursor_time, cursor_id = _decode_cursor(next_query_cursor)
            batch_query = batch_query.where(
                (TalentverseReport.updated_at < cursor_time)
                | ((TalentverseReport.updated_at == cursor_time) & (TalentverseReport.id < cursor_id))
            )
        rows = (
            db.execute(
                batch_query.order_by(TalentverseReport.updated_at.desc(), TalentverseReport.id.desc()).limit(batch_size)
            )
            .scalars()
            .all()
        )
        if not rows:
            break
        for row in rows:
            translation = _translation_for_locale(row, requested_locale)
            if translation is not None:
                matches.append((row, translation))
                if len(matches) > normalized_limit:
                    break
        if len(matches) > normalized_limit or len(rows) < batch_size:
            break
        next_query_cursor = _encode_cursor(rows[-1])

    page_matches = matches[:normalized_limit]
    next_cursor = _encode_cursor(page_matches[-1][0]) if len(matches) > normalized_limit and page_matches else None
    return {
        "items": [
            _list_item(row, translation)
            for row, translation in page_matches
        ],
        "pageInfo": {"limit": normalized_limit, "nextCursor": next_cursor},
    }


def get_published_talentverse_report_by_slug(db: Session, *, slug: str) -> dict | None:
    report = db.execute(
        select(TalentverseReport).where(TalentverseReport.slug == slug, TalentverseReport.status == PUBLISHED_STATUS)
    ).scalar_one_or_none()
    if report is not None:
        return _detail_item(report, _translation_for_slug(report, slug) or _legacy_payload(report))

    reports = db.execute(select(TalentverseReport).where(TalentverseReport.status == PUBLISHED_STATUS)).scalars().all()
    for candidate in reports:
        translation = _translation_for_slug(candidate, slug)
        if translation is not None:
            return _detail_item(candidate, translation)
    return None


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        return 20
    return min(limit, MAX_LIMIT)


def _list_item(report: TalentverseReport, payload: dict) -> dict:
    return {
        "id": payload.get("id") or f"tv-report-{report.id}",
        "slug": payload.get("slug") or report.slug,
        "region": payload.get("region") or report.region,
        "locale": payload.get("locale") or report.locale,
        "title": payload.get("title") or report.title,
        "subtitle": payload.get("subtitle"),
        "executiveSummary": payload.get("executiveSummary"),
        "keySignals": list(payload.get("keySignals") or [])[:3],
        "methodologyNote": _methodology_summary(payload.get("methodologyNote")),
        "source": payload.get("source"),
        "seo": payload.get("seo"),
        "publishedAt": _iso(report.published_at),
        "updatedAt": _iso(report.updated_at),
        "version": report.version,
        "category": payload.get("category"),
        "tags": payload.get("tags") or [],
        "translationGroupId": payload.get("translationGroupId"),
        "alternates": payload.get("alternates") or {},
    }


def _detail_item(report: TalentverseReport, payload: dict) -> dict:
    payload = dict(payload or {})
    payload["id"] = payload.get("id") or f"tv-report-{report.id}"
    payload["slug"] = payload.get("slug") or report.slug
    payload["region"] = payload.get("region") or report.region
    payload["locale"] = payload.get("locale") or report.locale
    payload["status"] = report.status
    payload["publishedAt"] = payload.get("publishedAt") or _iso(report.published_at)
    payload["updatedAt"] = payload.get("updatedAt") or _iso(report.updated_at)
    payload["version"] = payload.get("version") or report.version
    return payload


def _legacy_payload(report: TalentverseReport) -> dict:
    return dict(report.payload or {})


def _translation_for_locale(report: TalentverseReport, locale: str) -> dict | None:
    translations = _published_translations(report)
    return translations.get(locale)


def _translation_for_slug(report: TalentverseReport, slug: str) -> dict | None:
    for translation in _published_translations(report).values():
        if translation.get("slug") == slug:
            return translation
    legacy_payload = _legacy_payload(report)
    if report.slug == slug and legacy_payload:
        return legacy_payload
    return None


def _published_translations(report: TalentverseReport) -> dict[str, dict]:
    payload = _legacy_payload(report)
    translations = payload.get("translations")
    if isinstance(translations, dict):
        return {
            locale: translation
            for locale, translation in translations.items()
            if isinstance(translation, dict) and translation.get("status") == PUBLISHED_STATUS
        }
    return {report.locale: payload} if payload else {}


def _methodology_summary(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {"sampleCount": value.get("sampleCount"), "windowDays": value.get("windowDays")}


def _iso(value: datetime | None) -> str | None:
    return value.replace(microsecond=0).isoformat() if value is not None else None


def _encode_cursor(report: TalentverseReport) -> str:
    return f"{report.updated_at.isoformat()}::{report.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        timestamp, id_text = cursor.split("::", 1)
        return datetime.fromisoformat(timestamp), int(id_text)
    except (ValueError, TypeError) as exc:
        raise TalentverseCursorError("Invalid cursor") from exc
