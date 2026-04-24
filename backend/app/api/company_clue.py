from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.company_clue import CompanyClueRequest, CompanyClueResponse
from app.services.company_clue_letter import generate_company_clue_letter

router = APIRouter(prefix="/company-clue", tags=["company-clue"])


@router.post("", response_model=CompanyClueResponse)
def create_company_clue(payload: CompanyClueRequest, db: Session = Depends(get_db)):
    return generate_company_clue_letter(db, company=payload.company.strip())
