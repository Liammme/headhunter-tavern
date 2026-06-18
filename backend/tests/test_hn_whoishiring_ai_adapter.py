from __future__ import annotations

from app.crawlers.adapters.hn_whoishiring_ai import HNWhoIsHiringAIAdapter


def test_hn_whoishiring_ai_fetches_ai_comments_with_contacts(monkeypatch):
    requests: list[str] = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, url: str, params=None):
            requests.append(url)
            if url == "https://hn.algolia.com/api/v1/search_by_date":
                if params == {"query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 20}:
                    return FakeResponse(
                        {
                            "hits": [
                                {
                                    "objectID": "48392632",
                                    "title": 'Show HN: LiveComment "Who Is Hiring?" Plugin',
                                },
                                {
                                    "objectID": "48357725",
                                    "title": "Ask HN: Who is hiring? (June 2026)",
                                },
                            ]
                        }
                    )
                assert params == {
                    "tags": "comment,story_48357725",
                    "numericFilters": "parent_id=48357725",
                    "hitsPerPage": 1000,
                }
                return FakeResponse(
                    {
                        "hits": [
                            {
                                "objectID": "101",
                                "comment_text": "Signal Labs | AI Engineer | Remote<p>Build LLM agents. Email ai@signal.example</p>",
                                "created_at_i": 1781769600,
                                "parent_id": 48357725,
                                "story_id": 48357725,
                                "story_title": "Ask HN: Who is hiring? (June 2026)",
                            },
                            {
                                "objectID": "102",
                                "comment_text": "Back Office Inc | Accountant | Remote<p>Email jobs@backoffice.example</p>",
                                "parent_id": 48357725,
                            },
                            {
                                "objectID": "103",
                                "comment_text": "Model Lab | Machine Learning Engineer | Remote<p>Apply through our website.</p>",
                                "parent_id": 48357725,
                            },
                            {
                                "objectID": "104",
                                "comment_text": "Helpdesk Co | Customer Support Agent | Remote<p>Email support@example.com</p>",
                                "parent_id": 48357725,
                            },
                        ]
                    }
                )
            raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.crawlers.adapters.hn_whoishiring_ai.httpx.Client", FakeClient)

    jobs = HNWhoIsHiringAIAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "101"
    assert job.canonical_url == "https://news.ycombinator.com/item?id=101"
    assert job.title == "AI Engineer"
    assert job.company == "Signal Labs"
    assert job.location == "Remote"
    assert job.remote_type == "remote"
    assert "Build LLM agents" in job.description
    assert "ai@signal.example" in job.description
    assert job.raw_payload == {
        "site": "hn_whoishiring_ai",
        "story_id": "48357725",
        "story_title": "Ask HN: Who is hiring? (June 2026)",
        "story_url": "https://news.ycombinator.com/item?id=48357725",
        "company_url": "",
    }
    assert requests == [
        "https://hn.algolia.com/api/v1/search_by_date",
        "https://hn.algolia.com/api/v1/search_by_date",
    ]


def test_hn_whoishiring_ai_is_registered_as_global_adapter():
    from app.crawlers.registry import ADAPTERS

    assert ADAPTERS["hn_whoishiring_ai"] is HNWhoIsHiringAIAdapter
