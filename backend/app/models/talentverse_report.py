from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TalentverseReport(Base):
    __tablename__ = "talentverse_reports"
    __table_args__ = (
        UniqueConstraint("raw_report_id", name="uq_talentverse_reports_raw_report_id"),
        UniqueConstraint("slug", name="uq_talentverse_reports_slug"),
        CheckConstraint("status IN ('draft', 'published', 'failed')", name="ck_talentverse_reports_status"),
        Index(
            "ix_talentverse_reports_public_feed",
            "status",
            "region",
            "locale",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_report_id: Mapped[int] = mapped_column(Integer, index=True)
    slug: Mapped[str] = mapped_column(String(255), index=True)
    region: Mapped[str] = mapped_column(String(32), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
