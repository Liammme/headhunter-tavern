from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.bd_contacts_auth import require_bd_contacts_api_token
from app.db.database import get_db
from app.schemas.bd_contact import BdContactListResponse
from app.services.bd_contact_read_service import (
    build_bd_contacts_csv,
    list_bd_contacts,
    serialize_bd_contact,
)

router = APIRouter(
    prefix="/bd-contacts",
    tags=["bd-contacts"],
    dependencies=[Depends(require_bd_contacts_api_token)],
)


@router.get("", response_model=BdContactListResponse)
def list_contacts(
    region: Literal["global", "japan"] = Query(...),
    status: Literal["active", "stale"] = Query(default="active"),
    contactType: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    contacts = list_bd_contacts(
        db,
        region=region,
        status=status,
        contact_type=contactType,
        limit=limit,
        offset=offset,
    )
    return {
        "region": region,
        "items": [serialize_bd_contact(contact) for contact in contacts],
        "pageInfo": {"limit": limit, "offset": offset, "count": len(contacts)},
    }


@router.get("/export.csv")
def export_contacts_csv(
    region: Literal["global", "japan"] = Query(...),
    status: Literal["active", "stale"] = Query(default="active"),
    contactType: str | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    contacts = list_bd_contacts(
        db,
        region=region,
        status=status,
        contact_type=contactType,
        limit=limit,
        offset=offset,
    )
    csv_body = build_bd_contacts_csv(contacts)
    filename = f"bd-contacts-{region}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
