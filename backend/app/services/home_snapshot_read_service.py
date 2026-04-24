from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompanyDailySummary, IntelligenceSnapshot

SNAPSHOT_NOT_READY_REASON = "CompanyDailySummary 缺少岗位卡完整字段，不能直接替代 /api/v1/home。"


def load_home_snapshot_candidate(db: Session, *, snapshot_date: date) -> dict:
    company_summaries = _load_company_summaries(db, snapshot_date=snapshot_date)
    intelligence = _load_latest_intelligence_snapshot(db)
    blocking_reasons = _build_blocking_reasons(
        has_company_summaries=bool(company_summaries),
        has_intelligence=intelligence is not None,
    )

    return {
        "snapshot_date": snapshot_date.isoformat(),
        "ready_for_home": False,
        "blocking_reasons": blocking_reasons,
        "company_summaries": company_summaries,
        "intelligence": intelligence,
    }


def _load_company_summaries(db: Session, *, snapshot_date: date) -> list[dict]:
    summaries = (
        db.execute(
            select(CompanyDailySummary)
            .where(CompanyDailySummary.summary_date == snapshot_date)
            .order_by(
                CompanyDailySummary.company_grade.asc(),
                CompanyDailySummary.job_count.desc(),
                CompanyDailySummary.company_display_name.asc(),
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "company": summary.company_display_name,
            "company_normalized": summary.company_normalized,
            "company_grade": summary.company_grade,
            "job_count": summary.job_count,
            "representative_job_ids": list(summary.representative_job_ids or []),
            "claimed_names": list(summary.claimed_names or []),
        }
        for summary in summaries
    ]


def _load_latest_intelligence_snapshot(db: Session) -> dict | None:
    snapshot = (
        db.execute(select(IntelligenceSnapshot).order_by(IntelligenceSnapshot.generated_at.desc(), IntelligenceSnapshot.id.desc()))
        .scalars()
        .first()
    )
    if snapshot is None:
        return None
    return dict(snapshot.snapshot_payload or {})


def _build_blocking_reasons(*, has_company_summaries: bool, has_intelligence: bool) -> list[str]:
    reasons: list[str] = []
    if not has_company_summaries:
        reasons.append("缺少 CompanyDailySummary 日级公司快照。")
    if not has_intelligence:
        reasons.append("缺少 IntelligenceSnapshot 情报快照。")
    reasons.append(SNAPSHOT_NOT_READY_REASON)
    return reasons
