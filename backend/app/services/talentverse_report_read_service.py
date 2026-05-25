from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TalentverseReport

PUBLISHED_STATUS = "published"
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
    if locale:
        query = query.where(TalentverseReport.locale == locale)
    if updated_after is not None:
        query = query.where(TalentverseReport.updated_at > updated_after)
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        query = query.where(
            (TalentverseReport.updated_at < cursor_time)
            | ((TalentverseReport.updated_at == cursor_time) & (TalentverseReport.id < cursor_id))
        )

    rows = (
        db.execute(
            query.order_by(TalentverseReport.updated_at.desc(), TalentverseReport.id.desc()).limit(normalized_limit + 1)
        )
        .scalars()
        .all()
    )
    page_rows = rows[:normalized_limit]
    next_cursor = _encode_cursor(page_rows[-1]) if len(rows) > normalized_limit and page_rows else None
    return {
        "items": [_list_item(row) for row in page_rows],
        "pageInfo": {"limit": normalized_limit, "nextCursor": next_cursor},
    }


def get_published_talentverse_report_by_slug(db: Session, *, slug: str) -> dict | None:
    report = db.execute(
        select(TalentverseReport).where(TalentverseReport.slug == slug, TalentverseReport.status == PUBLISHED_STATUS)
    ).scalar_one_or_none()
    if report is None:
        return None
    return _detail_item(report)


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        return 20
    return min(limit, MAX_LIMIT)


def _list_item(report: TalentverseReport) -> dict:
    payload = dict(report.payload or {})
    return {
        "id": payload.get("id") or f"tv-report-{report.id}",
        "slug": report.slug,
        "region": report.region,
        "locale": report.locale,
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
    }


def _detail_item(report: TalentverseReport) -> dict:
    payload = dict(report.payload or {})
    payload["id"] = payload.get("id") or f"tv-report-{report.id}"
    payload["slug"] = report.slug
    payload["region"] = report.region
    payload["locale"] = report.locale
    payload["status"] = report.status
    payload["publishedAt"] = payload.get("publishedAt") or _iso(report.published_at)
    payload["updatedAt"] = payload.get("updatedAt") or _iso(report.updated_at)
    payload["version"] = payload.get("version") or report.version
    return payload


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
