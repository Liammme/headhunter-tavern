from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MarketIntelligenceFact(Base):
    __tablename__ = "market_intelligence_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    company_normalized: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    job_function: Mapped[str] = mapped_column(String(64), default="其他", index=True)
    market_theme: Mapped[str] = mapped_column(String(64), default="other", index=True)
    seniority: Mapped[str] = mapped_column(String(64), default="none", index=True)
    tech_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    business_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    salary_signal: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    fact_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
