from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.home import HomePayload
from app.services.home_query_service import get_home_payload

router = APIRouter(prefix="/home", tags=["home"])


@router.get("", response_model=HomePayload)
def get_home(db: Session = Depends(get_db)):
    return get_home_payload(db)
