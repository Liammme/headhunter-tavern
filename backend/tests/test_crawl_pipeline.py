from datetime import datetime, timedelta

from app.crawlers.base import NormalizedJob, SourceAdapter


class FakeTodayAdapter(SourceAdapter):
    source_name = "fake_today"

    def fetch(self) -> list[NormalizedJob]:
        now = datetime.now().replace(microsecond=0)
        return [
            NormalizedJob(
                source_job_id="og-staff-ai",
                canonical_url="https://jobs.example.com/opengradient/staff-ai-engineer",
                title="Staff AI Engineer",
                company="OpenGradient",
                location="Remote",
                remote_type="remote",
                employment_type="full-time",
                description="Build core AI infra and hiring roadmap.",
                posted_at=now,
                raw_payload={},
            ),
            NormalizedJob(
                source_job_id="og-product",
                canonical_url="https://jobs.example.com/opengradient/senior-product-manager",
                title="Senior Product Manager",
                company="OpenGradient",
                location="Remote",
                remote_type="remote",
                employment_type="full-time",
                description="Own product strategy and GTM collaboration.",
                posted_at=now,
                raw_payload={},
            ),
        ]


class FakeHistoryAdapter(SourceAdapter):
    source_name = "fake_history"

    def fetch(self) -> list[NormalizedJob]:
        now = datetime.now().replace(microsecond=0)
        return [
            NormalizedJob(
                source_job_id="chainsight-growth",
                canonical_url="https://jobs.example.com/chainsight/growth-product-manager",
                title="Growth Product Manager",
                company="ChainSight",
                location="Singapore",
                remote_type="unknown",
                employment_type="full-time",
                description="Growth product role with ecosystem exposure.",
                posted_at=now - timedelta(days=1),
                raw_payload={},
            ),
            NormalizedJob(
                source_job_id="atlas-backend",
                canonical_url="https://jobs.example.com/atlas-wallet/senior-backend-engineer",
                title="Senior Backend Engineer",
                company="Atlas Wallet",
                location="Hong Kong",
                remote_type="unknown",
                employment_type="full-time",
                description="Core backend for wallet and payment systems.",
                posted_at=now - timedelta(days=3),
                raw_payload={},
            ),
        ]


def install_fake_adapters(monkeypatch):
    from app.services import crawl_pipeline

    monkeypatch.setattr(
        crawl_pipeline,
        "ADAPTERS",
        {
            "fake_today": FakeTodayAdapter,
            "fake_history": FakeHistoryAdapter,
        },
    )


def test_trigger_crawl_populates_grouped_home_payload(client, monkeypatch):
    install_fake_adapters(monkeypatch)

    response = client.post("/api/v1/crawl/trigger")

    assert response.status_code == 200
    assert response.json()["status"] == "triggered"

    home_response = client.get("/api/v1/home")

    assert home_response.status_code == 200
    payload = home_response.json()
    assert [day["bucket"] for day in payload["days"]] == ["today", "yesterday", "earlier"]
    today_companies = payload["days"][0]["companies"]
    assert today_companies[0]["company"] == "OpenGradient"
    assert today_companies[0]["total_jobs"] == 2
    assert today_companies[0]["jobs"][0]["tags"]


def test_claim_persists_and_surfaces_in_home_payload(client, monkeypatch):
    install_fake_adapters(monkeypatch)
    client.post("/api/v1/crawl/trigger")
    home_response = client.get("/api/v1/home")
    job_id = home_response.json()["days"][0]["companies"][0]["jobs"][0]["id"]

    claim_response = client.post(
        "/api/v1/claims",
        json={"job_id": job_id, "claimer_name": "Liam"},
    )

    assert claim_response.status_code == 200

    refreshed_home = client.get("/api/v1/home")
    first_company = refreshed_home.json()["days"][0]["companies"][0]
    first_job = first_company["jobs"][0]

    assert first_job["claimed_names"] == []
    assert "Liam" in first_company["claimed_names"]
    assert first_company["claimed_by"] == "Liam"
    assert first_company["claim_status"] == "claimed"
