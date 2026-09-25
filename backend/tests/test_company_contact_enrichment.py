from datetime import datetime, timedelta

import httpx
import pytest

from app.models import BdContact, Job
from app.services.company_contact_enrichment import (
    FetchedCompanyPage,
    PublicWebsiteContactProvider,
    enrich_company_contacts,
    normalize_company_website,
)


def _job(*, url: str, description: str = "No contact") -> Job:
    return Job(
        canonical_url="https://jobs.example.com/acme/ai-engineer",
        source_name="dejob",
        region="global",
        title="AI Engineer",
        company="Acme",
        company_normalized="acme",
        description=description,
        collected_at=datetime(2026, 9, 25, 9, 0, 0),
        signal_tags={"company_url": url},
    )


def test_normalize_company_website_rejects_job_boards_social_sites_and_private_hosts():
    assert normalize_company_website("https://remoteok.com/jobs/1") is None
    assert normalize_company_website("https://www.linkedin.com/company/acme") is None
    assert normalize_company_website("http://127.0.0.1:8080/contact") is None
    assert normalize_company_website("http://224.0.0.1/contact") is None
    assert normalize_company_website("https://acme.example:invalid/contact") is None
    assert normalize_company_website("https://careers.acme.example/jobs/1") == "https://careers.acme.example/"


def test_public_website_provider_accepts_same_domain_business_emails_only():
    pages = {
        "https://acme.example/": FetchedCompanyPage(
            url="https://acme.example/",
            html='''
                <a href="/contact">Contact</a>
                <p>Write to hello@acme.example.</p>
                <p>Ignore jobs@acme.example and outside@gmail.com.</p>
            ''',
        ),
        "https://acme.example/contact": FetchedCompanyPage(
            url="https://acme.example/contact",
            html='<a href="mailto:founder@acme.example">Founder</a>',
        ),
    }
    provider = PublicWebsiteContactProvider(fetch_page=pages.__getitem__, max_pages=3)

    candidates = provider.discover("https://acme.example/")

    assert [(item.contact_value, item.confidence) for item in candidates] == [
        ("hello@acme.example", "medium"),
        ("founder@acme.example", "high"),
    ]
    assert all("Official company website:" in item.evidence_snippet for item in candidates)


class _Provider:
    def __init__(self):
        self.calls: list[str] = []

    def discover(self, company_url: str):
        from app.services.bd_contact_extraction import BdContactCandidate

        self.calls.append(company_url)
        return [
            BdContactCandidate(
                contact_type="email",
                contact_value="founder@acme.example",
                confidence="high",
                evidence_snippet="Official company website: https://acme.example/contact",
            )
        ]


def test_enrich_company_contacts_persists_metadata_and_active_email(db_session):
    job = _job(url="https://acme.example/about")
    db_session.add(job)
    db_session.commit()
    provider = _Provider()

    result = enrich_company_contacts(
        db_session,
        provider=provider,
        now=datetime(2026, 9, 25, 10, 0, 0),
        max_domains=10,
    )

    db_session.refresh(job)
    email = db_session.query(BdContact).filter(BdContact.contact_type == "email").one()
    assert provider.calls == ["https://acme.example/"]
    assert result == {
        "status": "completed",
        "checked_domains": 1,
        "enriched_jobs": 1,
        "discovered_emails": 1,
        "errors": [],
    }
    assert job.signal_tags["contact_enrichment"]["status"] == "found"
    assert email.contact_value == "founder@acme.example"
    assert email.status == "active"


def test_enrich_company_contacts_skips_recent_checks_and_jobs_with_direct_email(db_session):
    recent = _job(url="https://acme.example")
    recent.signal_tags = {
        **recent.signal_tags,
        "contact_enrichment": {
            "provider": "official_company_website",
            "status": "no_contact",
            "checked_at": "2026-09-24T10:00:00",
            "emails": [],
        },
    }
    direct = _job(
        url="https://other.example",
        description="Email founder@other.example",
    )
    direct.canonical_url = "https://jobs.example.com/other/ai-engineer"
    db_session.add_all([recent, direct])
    db_session.commit()
    provider = _Provider()

    result = enrich_company_contacts(
        db_session,
        provider=provider,
        now=datetime(2026, 9, 25, 10, 0, 0),
        retry_after=timedelta(days=7),
    )

    assert provider.calls == []
    assert result["checked_domains"] == 0


def test_provider_rejects_cross_company_redirect_and_parent_domain_email():
    provider = PublicWebsiteContactProvider(fetch_page=lambda url: FetchedCompanyPage(
        url="https://other.example/", html="hello@acme.example",
    ))
    with pytest.raises(ValueError, match="another organization"):
        provider.discover("https://acme.example")

    provider = PublicWebsiteContactProvider(fetch_page=lambda url: FetchedCompanyPage(
        url=url, html='a@example a@other.acme.example <a href="mailto:jobs+us@acme.example">Apply</a>',
    ))
    assert provider.discover("https://acme.example") == []


def test_website_network_pins_public_ip_and_retains_tls_hostname(monkeypatch):
    from app.services import company_contact_enrichment as service

    monkeypatch.setattr(service.socket, "getaddrinfo", lambda *args, **kwargs: [
        (2, 1, 6, "", ("93.184.216.34", 443)),
    ])
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, text="<p>hello@acme.example</p>", headers={"Content-Type": "text/html"})

    client_class = httpx.Client
    monkeypatch.setattr(service.httpx, "Client", lambda **kwargs: client_class(
        transport=httpx.MockTransport(respond), **kwargs,
    ))
    page = service._fetch_public_company_page("https://acme.example/", timeout_seconds=2)
    assert page.url == "https://acme.example/"
    assert requests[0].url.host == "93.184.216.34"
    assert requests[0].headers["host"] == "acme.example"
    assert requests[0].extensions["sni_hostname"] == "acme.example"


def test_website_network_rejects_private_dns_and_cross_host_redirect(monkeypatch):
    from app.services import company_contact_enrichment as service

    monkeypatch.setattr(service.socket, "getaddrinfo", lambda *args, **kwargs: [
        (2, 1, 6, "", ("127.0.0.1", 443)),
    ])
    with pytest.raises(ValueError, match="private address"):
        service._fetch_public_company_page("https://acme.example/", timeout_seconds=2)

    monkeypatch.setattr(service.socket, "getaddrinfo", lambda *args, **kwargs: [
        (2, 1, 6, "", ("93.184.216.34", 443)),
    ])
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/contact"})

    client_class = httpx.Client
    monkeypatch.setattr(service.httpx, "Client", lambda **kwargs: client_class(
        transport=httpx.MockTransport(respond), **kwargs,
    ))
    with pytest.raises(ValueError, match="another organization"):
        service._fetch_public_company_page("https://acme.example/", timeout_seconds=2)
    assert len(requests) == 1


def test_enrichment_groups_domains_respects_cap_and_preserves_other_region(db_session):
    first = _job(url="https://acme.example")
    second = _job(url="https://acme.example/about")
    second.canonical_url += "-2"
    japan = _job(url="https://acme.example")
    japan.canonical_url += "-jp"
    japan.region = "japan"
    db_session.add_all([first, second, japan])
    db_session.commit()
    provider = _Provider()
    result = enrich_company_contacts(db_session, provider=provider, max_domains=1,
                                     now=datetime(2026, 9, 25, 10))
    assert len(provider.calls) == 1
    assert result["enriched_jobs"] == 2
    assert "contact_enrichment" not in japan.signal_tags
    assert db_session.query(BdContact).filter(BdContact.contact_type == "email").count() == 2


def test_enrichment_failure_is_recorded_without_erasing_known_contacts(db_session):
    from app.services.bd_contact_service import refresh_bd_contacts_for_job

    job = _job(url="https://acme.example")
    job.signal_tags = {**job.signal_tags, "contact_enrichment": {
        "provider": "official_company_website", "status": "found", "checked_at": "2026-09-01T00:00:00",
        "emails": [{"value": "hello@acme.example", "evidence_url": "https://acme.example/"}],
    }}
    db_session.add(job)
    db_session.flush()
    refresh_bd_contacts_for_job(db_session, job)
    db_session.commit()

    class FailedProvider:
        def discover(self, url):
            raise httpx.ConnectTimeout("request timed out")

    result = enrich_company_contacts(db_session, provider=FailedProvider(), now=datetime(2026, 9, 25, 10))
    assert result["errors"] == ["acme.example: ConnectTimeout"]
    assert job.signal_tags["contact_enrichment"]["status"] == "error"
    refresh_bd_contacts_for_job(db_session, job)
    assert db_session.query(BdContact).filter(BdContact.contact_type == "email").one().status == "active"
