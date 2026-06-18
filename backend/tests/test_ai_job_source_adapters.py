from __future__ import annotations

from app.crawlers.adapters.jobicy_ai import JobicyAIAdapter
from app.crawlers.adapters.remoteok_ai import RemoteOKAIAdapter


def test_jobicy_ai_filters_ai_related_jobs_and_preserves_email(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": 101,
                "url": "https://jobicy.com/jobs/101-ai-engineer",
                "jobSlug": "101-ai-engineer",
                "jobTitle": "AI Engineer",
                "companyName": "Signal Labs",
                "jobGeo": "Worldwide",
                "jobType": ["Full-Time"],
                "jobLevel": "Senior",
                "jobDescription": "<p>Build LLM agents. Apply via jobs@signal.example.</p>",
                "pubDate": "2026-06-18T14:06:46+08:00",
            },
            {
                "id": 102,
                "url": "https://jobicy.com/jobs/102-accountant",
                "jobSlug": "102-accountant",
                "jobTitle": "Accountant",
                "companyName": "Back Office Inc",
                "jobGeo": "Europe",
                "jobType": ["Full-Time"],
                "jobDescription": "<p>Accounting role using AI productivity tools.</p>",
            },
        ]
    }

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, url: str):
            assert url == "https://jobicy.com/api/v2/remote-jobs?count=100"
            return FakeResponse()

    monkeypatch.setattr("app.crawlers.adapters.jobicy_ai.httpx.Client", FakeClient)

    jobs = JobicyAIAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "101"
    assert job.canonical_url == "https://jobicy.com/jobs/101-ai-engineer"
    assert job.title == "AI Engineer"
    assert job.company == "Signal Labs"
    assert job.location == "Worldwide"
    assert job.remote_type == "remote"
    assert job.employment_type == "Full-Time"
    assert "Build LLM agents" in job.description
    assert "jobs@signal.example" in job.description
    assert job.raw_payload == {"site": "jobicy_ai", "job_slug": "101-ai-engineer", "company_url": ""}


def test_remoteok_ai_parses_feed_and_preserves_contact_fields(monkeypatch):
    payload = [
        {"last_updated": 1781769603, "legal": "terms"},
        {
            "id": "201",
            "slug": "remote-ai-researcher-signal-labs-201",
            "url": "https://remoteOK.com/remote-jobs/remote-ai-researcher-signal-labs-201",
            "apply_url": "https://signal.example/careers/201",
            "company": "Signal Labs",
            "position": "AI Researcher",
            "location": "Worldwide",
            "tags": ["ai", "machine learning"],
            "description": "<p>Research LLM evaluation. Email hiring@signal.example.</p>",
            "date": "2026-06-08T15:03:02+00:00",
        },
        {
            "id": "202",
            "url": "https://remoteOK.com/remote-jobs/remote-client-delivery-manager-202",
            "company": "SaaS Co",
            "position": "Client Delivery Manager",
            "tags": ["ai", "saas"],
            "description": "<p>Client delivery role at an AI company.</p>",
        },
    ]

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict]:
            return payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, url: str):
            assert url == "https://remoteok.com/api?tags=ai"
            return FakeResponse()

    monkeypatch.setattr("app.crawlers.adapters.remoteok_ai.httpx.Client", FakeClient)

    jobs = RemoteOKAIAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "201"
    assert job.canonical_url == "https://remoteOK.com/remote-jobs/remote-ai-researcher-signal-labs-201"
    assert job.title == "AI Researcher"
    assert job.company == "Signal Labs"
    assert job.location == "Worldwide"
    assert job.remote_type == "remote"
    assert job.employment_type == "unknown"
    assert "Research LLM evaluation" in job.description
    assert "hiring@signal.example" in job.description
    assert job.raw_payload == {
        "site": "remoteok_ai",
        "apply_url": "https://signal.example/careers/201",
        "company_url": "https://signal.example/careers/201",
        "tags": ["ai", "machine learning"],
    }


def test_ai_job_sources_are_registered_as_global_adapters():
    from app.crawlers.registry import ADAPTERS

    assert ADAPTERS["jobicy_ai"] is JobicyAIAdapter
    assert ADAPTERS["remoteok_ai"] is RemoteOKAIAdapter
