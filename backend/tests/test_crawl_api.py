def test_trigger_crawl_endpoint_returns_service_result(client, monkeypatch):
    expected = {
        "status": "triggered",
        "new_jobs": 2,
        "fetched_jobs": 4,
        "source_stats": {"demo": 4},
        "errors": [],
    }

    monkeypatch.setattr("app.api.crawl.trigger_crawl_service", lambda db: expected)

    response = client.post("/api/v1/crawl/trigger")

    assert response.status_code == 200
    assert response.json() == expected
