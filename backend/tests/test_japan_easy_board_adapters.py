from app.crawlers.adapters.en_tenshoku import EnTenshokuAdapter
from app.crawlers.adapters.yolo_japan import YoloJapanAdapter


def test_en_tenshoku_adapter_parses_new_job_links(monkeypatch):
    html = """
    <a href="/desc_1418422/?arearoute=1">
      厚生労働省の管理部門担当◆政策の推進を支援する仕事／テレワーク可 職種未経験OK 業種未経験OK
    </a>
    <a href="/desc_1418422/?arearoute=1">詳細へ</a>
    """
    monkeypatch.setattr("app.crawlers.adapters.en_tenshoku.fetch_html", lambda url: html)

    jobs = EnTenshokuAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://employment.en-japan.com/desc_1418422/?arearoute=1"
    assert jobs[0].title.startswith("厚生労働省の管理部門担当")
    assert jobs[0].source_job_id == "1418422"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].raw_payload["site"] == "en_tenshoku"


def test_yolo_japan_adapter_parses_public_json(monkeypatch):
    payload = {
        "code": "success",
        "jobData": {
            "partTime": [
                [
                    {
                        "id": 33960,
                        "jobId": 35062,
                        "title": "Full-time employees/experienced hotel front staff",
                        "companyName": "YOLO Hotel",
                        "prefecture": "Tokyo",
                        "city": "Shinjuku",
                    }
                ]
            ]
        },
    }
    monkeypatch.setattr("app.crawlers.adapters.yolo_japan.fetch_json", lambda url: payload)

    jobs = YoloJapanAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://www.yolo-japan.com/en/recruit/job/details/35062"
    assert jobs[0].title == "Full-time employees/experienced hotel front staff"
    assert jobs[0].company == "YOLO Hotel"
    assert jobs[0].location == "Tokyo, Shinjuku"
    assert jobs[0].source_job_id == "35062"
    assert jobs[0].raw_payload["site"] == "yolo_japan"
