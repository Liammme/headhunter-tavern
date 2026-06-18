from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class BdContact(Base):
    __tablename__ = "bd_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)
    region: Mapped[str] = mapped_column(String(32), index=True)
    company: Mapped[str] = mapped_column(String(256))
    company_normalized: Mapped[str] = mapped_column(String(256), index=True)
    job_title: Mapped[str] = mapped_column(Text)
    contact_type: Mapped[str] = mapped_column(String(32), index=True)
    contact_value: Mapped[str] = mapped_column(String(512))
    normalized_value: Mapped[str] = mapped_column(String(512), index=True)
    confidence: Mapped[str] = mapped_column(String(16), index=True)
    source_name: Mapped[str] = mapped_column(String(64), index=True)
    job_url: Mapped[str] = mapped_column(String(1024))
    company_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    evidence_snippet: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
