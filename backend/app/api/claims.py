from fastapi import APIRouter

from app.schemas.claim import ClaimCreate

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("")
def create_claim(payload: ClaimCreate):
    return {
        "job_id": payload.job_id,
        "claimer_name": payload.claimer_name,
    }
