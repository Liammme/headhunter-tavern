from datetime import datetime

from app.models import BdContact


def _add_contact(db_session, *, region: str, contact_type: str, contact_value: str) -> BdContact:
    now = datetime(2026, 6, 18, 9, 0, 0)
    contact = BdContact(
        dedupe_key=f"{region}:https://example.com/job:{contact_type}:{contact_value}",
        job_id=1,
        region=region,
        company="Example",
        company_normalized="example",
        job_title="BD Manager",
        contact_type=contact_type,
        contact_value=contact_value,
        normalized_value=contact_value.lower(),
        confidence="high",
        source_name="abetterweb3",
        job_url="https://example.com/job",
        company_url="https://example.com",
        evidence_snippet="Contact hr@example.com",
        status="active",
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


def test_bd_contacts_requires_bearer_token(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.bd_contacts_auth.settings.bd_contacts_api_token", "secret-token")
    _add_contact(db_session, region="global", contact_type="email", contact_value="hr@example.com")

    response = client.get("/api/v1/bd-contacts?region=global")

    assert response.status_code == 401


def test_bd_contacts_lists_contacts_by_region(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.bd_contacts_auth.settings.bd_contacts_api_token", "secret-token")
    _add_contact(db_session, region="global", contact_type="email", contact_value="global@example.com")
    _add_contact(db_session, region="japan", contact_type="telegram", contact_value="@japanlead")

    response = client.get(
        "/api/v1/bd-contacts?region=japan",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["region"] == "japan"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["contactType"] == "telegram"
    assert payload["items"][0]["contactValue"] == "@japanlead"


def test_bd_contacts_exports_csv_by_region(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.bd_contacts_auth.settings.bd_contacts_api_token", "secret-token")
    _add_contact(db_session, region="global", contact_type="email", contact_value="global@example.com")
    _add_contact(db_session, region="japan", contact_type="email", contact_value="japan@example.com")

    response = client.get(
        "/api/v1/bd-contacts/export.csv?region=global",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "global@example.com" in body
    assert "japan@example.com" not in body
