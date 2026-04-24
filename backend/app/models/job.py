from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_url: Mapped[str] = mapped_column(String(1024), unique=True)
    source_name: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(String(256))
    company_normalized: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    job_category: Mapped[str] = mapped_column(String(64), default="其他")
    domain_tag: Mapped[str] = mapped_column(String(64), default="其他")
    bounty_grade: Mapped[str] = mapped_column(String(16), default="low")
    signal_tags: Mapped[dict] = mapped_column(JSON, default=dict)
