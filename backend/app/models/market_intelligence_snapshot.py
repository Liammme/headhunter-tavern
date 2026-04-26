from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MarketIntelligenceSnapshot(Base):
    __tablename__ = "market_intelligence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    window_days: Mapped[int] = mapped_column(Integer, default=90)
    market_signal_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    report_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
