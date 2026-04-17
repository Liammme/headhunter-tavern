from datetime import date

from sqlalchemy import Date, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class CompanyDailySummary(Base):
    __tablename__ = "company_daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_date: Mapped[date] = mapped_column(Date, index=True)
    company_normalized: Mapped[str] = mapped_column(String(256), index=True)
    company_display_name: Mapped[str] = mapped_column(String(256))
    company_grade: Mapped[str] = mapped_column(String(16), default="normal")
    job_count: Mapped[int] = mapped_column(Integer, default=0)
    representative_job_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    claimed_names: Mapped[list[str]] = mapped_column(JSON, default=list)
