from sqlalchemy.orm import Session

from app.services.home_feed import build_home_payload
from app.services.regional_home_feed import build_japan_home_payload


def get_home_payload(db: Session) -> dict:
    return build_home_payload(db)


def get_japan_home_payload(db: Session) -> dict:
    return build_japan_home_payload(db)
