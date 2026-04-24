from sqlalchemy.orm import Session

from app.services.crawl_pipeline import run_crawl


def trigger_crawl(db: Session) -> dict:
    return run_crawl(db)
