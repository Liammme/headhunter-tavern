from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class IntelligenceSnapshot(Base):
    __tablename__ = "intelligence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
