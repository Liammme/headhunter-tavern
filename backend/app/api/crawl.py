from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.crawl_trigger_service import trigger_crawl as trigger_crawl_service

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post("/trigger")
def trigger_crawl(db: Session = Depends(get_db)):
    return trigger_crawl_service(db)
