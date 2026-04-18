from app.services.home_query_service import get_home_payload


def test_get_home_payload_delegates_to_home_feed(db_session, monkeypatch):
    expected = {
        "intelligence": {"headline": "test", "summary": "test", "findings": [], "actions": []},
        "days": [],
    }
    captured = {}

    def fake_build_home_payload(db):
        captured["db"] = db
        return expected

    monkeypatch.setattr("app.services.home_query_service.build_home_payload", fake_build_home_payload)

    result = get_home_payload(db_session)

    assert result == expected
    assert captured["db"] is db_session
