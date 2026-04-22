def test_home_endpoint_returns_query_service_result(client, monkeypatch):
    expected = {
        "intelligence": {
            "narrative": "test",
            "headline": "test",
            "summary": "test",
            "analysis_version": "feed-v1",
            "rule_version": "score-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
            "findings": [],
            "actions": [],
        },
        "meta": {
            "analysis_version": "feed-v1",
            "rule_version": "score-v1",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
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
    assert "meta" in body
    assert "days" in body
    assert body["meta"]["analysis_version"] == "feed-v1"
    assert body["meta"]["rule_version"] == "score-v2"


def test_home_endpoint_keeps_company_url_when_present(client, monkeypatch):
    expected = {
        "intelligence": {
            "narrative": "test",
            "headline": "test",
            "summary": "test",
            "analysis_version": "feed-v1",
            "rule_version": "score-v2",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
            "findings": [],
            "actions": [],
        },
        "meta": {
            "analysis_version": "feed-v1",
            "rule_version": "score-v2",
            "window_start": "2026-04-05",
            "window_end": "2026-04-18",
            "generated_at": "2026-04-18T09:00:00",
        },
        "days": [
            {
                "bucket": "today",
                "companies": [
                    {
                        "company": "OpenGradient",
                        "company_url": "https://jobs.example.com/company/opengradient",
                        "company_grade": "focus",
                        "total_jobs": 1,
                        "claimed_names": [],
                        "jobs": [],
                    }
                ],
            }
        ],
    }

    monkeypatch.setattr("app.api.home.get_home_payload", lambda db: expected)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["days"][0]["companies"][0]["company_url"] == "https://jobs.example.com/company/opengradient"


def test_trigger_crawl_endpoint_exists(client):
    response = client.post("/api/v1/crawl/trigger")

    assert response.status_code == 200
    assert "triggered" in response.json()["status"]
