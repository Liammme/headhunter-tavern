from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.talentverse_auth import require_reports_api_token
from app.db.database import get_db
from app.schemas.talentverse_report import TalentverseReportListResponse
from app.services.talentverse_report_read_service import (
    TalentverseCursorError,
    get_published_talentverse_report_by_slug,
    list_published_talentverse_reports,
)

router = APIRouter(
    prefix="/talentverse/reports",
    tags=["talentverse-reports"],
    dependencies=[Depends(require_reports_api_token)],
)


@router.get("", response_model=TalentverseReportListResponse)
def list_reports(
    region: Literal["global", "japan"] | None = Query(default=None),
    locale: Literal["zh-CN", "ja-JP"] | None = Query(default=None),
    status: Literal["published"] = Query(default="published"),
    limit: int = Query(default=20),
    cursor: str | None = Query(default=None),
    updatedAfter: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        return list_published_talentverse_reports(
            db,
            region=region,
            locale=locale,
            status=status,
            limit=limit,
            cursor=cursor,
            updated_after=updatedAfter,
        )
    except TalentverseCursorError as exc:
        raise HTTPException(status_code=422, detail="Invalid cursor") from exc


@router.get("/{slug}")
def get_report(slug: str, db: Session = Depends(get_db)):
    report = get_published_talentverse_report_by_slug(db, slug=slug)
    if report is None:
        raise HTTPException(status_code=404, detail="Talentverse report not found")
    return report
