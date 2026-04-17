from fastapi import APIRouter

from app.schemas.home import HomePayload
from app.services.intelligence import build_intelligence_snapshot

router = APIRouter(prefix="/home", tags=["home"])


@router.get("", response_model=HomePayload)
def get_home():
    return {
        "intelligence": build_intelligence_snapshot(),
        "days": [],
    }
