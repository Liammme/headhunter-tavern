from app.db.database import Base, engine
from app.models import (
    company_daily_summary,
    intelligence_snapshot,
    job,
    job_claim,
    market_intelligence_fact,
    market_intelligence_snapshot,
)


def init_db() -> None:
    _ = (
        job,
        company_daily_summary,
        job_claim,
        intelligence_snapshot,
        market_intelligence_fact,
        market_intelligence_snapshot,
    )
    Base.metadata.create_all(bind=engine)
