from app.services.crawl_trigger_service import trigger_crawl


def test_trigger_crawl_delegates_to_pipeline(db_session, monkeypatch):
    expected = {"status": "triggered", "new_jobs": 3}
    captured = {}

    def fake_run_crawl(db):
        captured["db"] = db
        return expected

    monkeypatch.setattr("app.services.crawl_trigger_service.run_crawl", fake_run_crawl)

    result = trigger_crawl(db_session)

    assert result == expected
    assert captured["db"] is db_session
