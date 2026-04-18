def test_home_endpoint_returns_query_service_result(client, monkeypatch):
    expected = {
        "intelligence": {
            "headline": "test",
            "summary": "test",
            "findings": [],
            "actions": [],
        },
        "days": [],
    }

    monkeypatch.setattr("app.api.home.get_home_payload", lambda db: expected)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json() == expected


def test_home_payload_has_intelligence_and_days(client):
    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert "intelligence" in body
    assert "days" in body


def test_trigger_crawl_endpoint_exists(client):
    response = client.post("/api/v1/crawl/trigger")

    assert response.status_code == 200
    assert "triggered" in response.json()["status"]
