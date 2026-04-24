from sqlalchemy.orm import Session

from app.services.home_feed import build_home_payload


def get_home_payload(db: Session) -> dict:
    return build_home_payload(db)
