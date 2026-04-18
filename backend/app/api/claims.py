from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.claim import ClaimCreate
from app.services.claim_service import ClaimJobNotFoundError, create_claim as create_claim_record

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("")
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db)):
    try:
        claim = create_claim_record(db, job_id=payload.job_id, claimer_name=payload.claimer_name)
    except ClaimJobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": claim.id,
        "job_id": payload.job_id,
        "claimer_name": claim.claimer_name,
    }
