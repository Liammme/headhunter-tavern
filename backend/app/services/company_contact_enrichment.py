from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import ipaddress
import socket
from typing import Protocol
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.bd_contact_extraction import EMAIL_PATTERN, BdContactCandidate, extract_email_candidates
from app.services.bd_contact_service import refresh_bd_contacts_for_job


ENRICHMENT_KEY = "contact_enrichment"
PROVIDER_NAME = "official_company_website"
DEFAULT_RETRY_AFTER = timedelta(days=7)
DEFAULT_WINDOW = timedelta(days=30)

EXCLUDED_COMPANY_HOSTS = {
    "aijobs.net",
    "ashbyhq.com",
    "dejob.ai",
    "discourse.openrobotics.org",
    "discuss.pytorch.org",
    "foorilla.com",
    "glassdoor.com",
    "greenhouse.io",
    "indeed.com",
    "jobicy.com",
    "lever.co",
    "linkedin.com",
    "lnkd.in",
    "github.com",
    "facebook.com",
    "t.me",
    "myworkdayjobs.com",
    "remoteok.com",
    "twitter.com",
    "workatastartup.com",
    "workday.com",
    "x.com",
    "ycombinator.com",
}
EXCLUDED_EMAIL_LOCAL_PARTS = {
    "abuse",
    "apply",
    "applications",
    "career",
    "careers",
    "cv",
    "do-not-reply",
    "donotreply",
    "job",
    "jobs",
    "legal",
    "no-reply",
    "noreply",
    "privacy",
    "resume",
    "security",
    "support",
    "webmaster",
}
CONTACT_PAGE_KEYWORDS = ("contact", "about", "team", "people", "company")


@dataclass(frozen=True)
class FetchedCompanyPage:
    url: str
    html: str


class CompanyContactProvider(Protocol):
    def discover(self, company_url: str) -> list[BdContactCandidate]: ...


class PublicWebsiteContactProvider:
    def __init__(
        self,
        *,
        fetch_page: Callable[[str], FetchedCompanyPage] | None = None,
        max_pages: int = 3,
        timeout_seconds: int = 10,
    ) -> None:
        self._fetch_page = fetch_page or (
            lambda url: _fetch_public_company_page(url, timeout_seconds=timeout_seconds)
        )
        self._max_pages = max(1, max_pages)

    def discover(self, company_url: str) -> list[BdContactCandidate]:
        website = normalize_company_website(company_url)
        if website is None:
            return []

        company_host = urlsplit(website).hostname or ""
        queue = [website]
        visited: set[str] = set()
        candidates: list[BdContactCandidate] = []

        while queue and len(visited) < self._max_pages:
            requested_url = queue.pop(0)
            if requested_url in visited:
                continue
            page = self._fetch_page(requested_url)
            visited.add(requested_url)
            if not _same_organization_host(urlsplit(page.url).hostname or "", company_host):
                raise ValueError("company page redirected to another organization")
            candidates.extend(_extract_official_email_candidates(page, company_host=company_host))

            for link in _contact_page_links(page, company_host=company_host):
                if link not in visited and link not in queue:
                    queue.append(link)

        return _dedupe_email_candidates(candidates)[:10]


def enrich_company_contacts(
    db: Session,
    *,
    provider: CompanyContactProvider | None = None,
    region: str = "global",
    now: datetime | None = None,
    max_domains: int = 10,
    retry_after: timedelta = DEFAULT_RETRY_AFTER,
) -> dict:
    checked_at = now or datetime.now()
    contact_provider = provider or PublicWebsiteContactProvider()
    jobs = list(
        db.execute(
            select(Job)
            .where(
                Job.region == region,
                Job.collected_at >= checked_at - DEFAULT_WINDOW,
            )
            .order_by(Job.collected_at.desc(), Job.id.desc())
        ).scalars()
    )

    jobs_by_website: dict[str, list[Job]] = {}
    for job in jobs:
        website = normalize_company_website(_company_url(job))
        if website is None or _has_direct_job_email(job):
            continue
        if not _enrichment_is_due(job, now=checked_at, retry_after=retry_after):
            continue
        jobs_by_website.setdefault(website, []).append(job)

    checked_domains = 0
    enriched_jobs = 0
    discovered_emails = 0
    errors: list[str] = []

    for website, website_jobs in list(jobs_by_website.items())[: max(0, max_domains)]:
        checked_domains += 1
        try:
            candidates = contact_provider.discover(website)
        except Exception as exc:  # noqa: BLE001
            host = urlsplit(website).hostname or "unknown-host"
            errors.append(f"{host}: {exc.__class__.__name__}")
            for job in website_jobs:
                _record_enrichment_error(job, website=website, checked_at=checked_at)
            continue

        discovered_emails += len(candidates)
        for job in website_jobs:
            _record_enrichment_result(
                job,
                website=website,
                candidates=candidates,
                checked_at=checked_at,
            )
            refresh_bd_contacts_for_job(db, job)
            if candidates:
                enriched_jobs += 1

    db.commit()
    return {
        "status": "completed_with_errors" if errors else "completed",
        "checked_domains": checked_domains,
        "enriched_jobs": enriched_jobs,
        "discovered_emails": discovered_emails,
        "errors": errors,
    }


def normalize_company_website(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    host = parsed.hostname.lower().rstrip(".")
    if _is_excluded_host(host) or _is_non_public_literal_ip(host):
        return None

    netloc = host
    if port not in {None, 80, 443}:
        return None
    if ":" in host:
        return None
    if port:
        netloc = f"{host}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, "/", "", ""))


def _company_url(job: Job) -> str | None:
    tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    value = tags.get("company_url")
    return value if isinstance(value, str) else None


def _has_direct_job_email(job: Job) -> bool:
    text = "\n".join(value for value in (job.title or "", job.description or "") if value)
    return bool(extract_email_candidates(text))


def _enrichment_is_due(job: Job, *, now: datetime, retry_after: timedelta) -> bool:
    tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    state = tags.get(ENRICHMENT_KEY)
    if not isinstance(state, dict):
        return True
    checked_at = state.get("checked_at")
    if not isinstance(checked_at, str):
        return True
    try:
        last_checked = datetime.fromisoformat(checked_at)
    except ValueError:
        return True
    if last_checked.tzinfo is not None:
        last_checked = last_checked.replace(tzinfo=None)
    interval = min(retry_after, timedelta(days=1)) if state.get("status") == "error" else retry_after
    return last_checked <= now - interval


def _record_enrichment_result(
    job: Job,
    *,
    website: str,
    candidates: list[BdContactCandidate],
    checked_at: datetime,
) -> None:
    tags = dict(job.signal_tags) if isinstance(job.signal_tags, dict) else {}
    tags[ENRICHMENT_KEY] = {
        "provider": PROVIDER_NAME,
        "status": "found" if candidates else "no_contact",
        "checked_at": checked_at.replace(microsecond=0).isoformat(),
        "company_url": website,
        "emails": [
            {
                "value": candidate.contact_value,
                "confidence": candidate.confidence,
                "evidence_url": _evidence_url(candidate.evidence_snippet),
            }
            for candidate in candidates
        ],
    }
    job.signal_tags = tags


def _record_enrichment_error(job: Job, *, website: str, checked_at: datetime) -> None:
    tags = dict(job.signal_tags) if isinstance(job.signal_tags, dict) else {}
    previous = tags.get(ENRICHMENT_KEY)
    emails = previous.get("emails", []) if isinstance(previous, dict) else []
    tags[ENRICHMENT_KEY] = {
        "provider": PROVIDER_NAME,
        "status": "error",
        "checked_at": checked_at.replace(microsecond=0).isoformat(),
        "company_url": website,
        "emails": emails if isinstance(emails, list) else [],
    }
    job.signal_tags = tags


def _evidence_url(evidence_snippet: str) -> str:
    prefix = "Official company website:"
    if evidence_snippet.startswith(prefix):
        return evidence_snippet[len(prefix) :].strip()
    return ""


def _extract_official_email_candidates(
    page: FetchedCompanyPage,
    *,
    company_host: str,
) -> list[BdContactCandidate]:
    soup = BeautifulSoup(page.html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    mailto_values: set[str] = set()
    for anchor in soup.select("a[href^='mailto:']"):
        href = anchor.get("href", "")
        address = unquote(href[len("mailto:") :].split("?", 1)[0]).strip().lower()
        if address:
            mailto_values.add(address)

    text = soup.get_text(" ", strip=True)
    text_values = {candidate.contact_value for candidate in extract_email_candidates(text)}
    candidates: list[BdContactCandidate] = []
    for value in [*sorted(text_values), *sorted(mailto_values)]:
        if not _is_business_email_for_host(value, company_host=company_host):
            continue
        candidates.append(
            BdContactCandidate(
                contact_type="email",
                contact_value=value,
                confidence="high" if value in mailto_values else "medium",
                evidence_snippet=f"Official company website: {page.url}",
            )
        )
    return candidates


def _contact_page_links(page: FetchedCompanyPage, *, company_host: str) -> list[str]:
    soup = BeautifulSoup(page.html, "html.parser")
    links: list[str] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        url = urljoin(page.url, href)
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        path_and_label = f"{parsed.path} {anchor.get_text(' ', strip=True)}".lower()
        if not _same_organization_host(host, company_host):
            continue
        if not any(keyword in path_and_label for keyword in CONTACT_PAGE_KEYWORDS):
            continue
        normalized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))
        if normalized not in links:
            links.append(normalized)
    return links


def _dedupe_email_candidates(candidates: list[BdContactCandidate]) -> list[BdContactCandidate]:
    by_email: dict[str, BdContactCandidate] = {}
    for candidate in candidates:
        key = candidate.contact_value.lower()
        existing = by_email.get(key)
        if existing is None or (candidate.confidence == "high" and existing.confidence != "high"):
            by_email[key] = candidate
    return list(by_email.values())


def _is_business_email_for_host(value: str, *, company_host: str) -> bool:
    if not EMAIL_PATTERN.fullmatch(value):
        return False
    local_part, email_host = value.lower().rsplit("@", 1)
    if local_part.split("+", 1)[0] in EXCLUDED_EMAIL_LOCAL_PARTS:
        return False
    return _same_organization_host(email_host.rstrip("."), company_host.rstrip("."))


def _same_organization_host(first: str, second: str) -> bool:
    left = first.lower().removeprefix("www.")
    right = second.lower().removeprefix("www.")
    return bool(left and right and left == right)


def _is_excluded_host(host: str) -> bool:
    return any(host == excluded or host.endswith(f".{excluded}") for excluded in EXCLUDED_COMPANY_HOSTS)


def _is_non_public_literal_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host == "localhost"
    return not address.is_global or address.is_multicast


def _fetch_public_company_page(url: str, *, timeout_seconds: int) -> FetchedCompanyPage:
    current_url = url
    initial_host = urlsplit(url).hostname or ""
    headers = {
        "User-Agent": "TalentverseContactResearch/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    with httpx.Client(
        timeout=timeout_seconds, follow_redirects=False, headers=headers, trust_env=False,
        limits=httpx.Limits(max_keepalive_connections=0),
    ) as client:
        for _ in range(4):
            host = urlsplit(current_url).hostname or ""
            if not _same_organization_host(host, initial_host):
                raise ValueError("company page redirected to another organization")
            address = _assert_public_network_url(current_url)
            # Connect to the validated IP so DNS cannot change between validation and use.
            original = httpx.URL(current_url)
            pinned = original.copy_with(host=address)
            with client.stream(
                "GET", pinned, headers={"Host": original.netloc.decode("ascii")},
                extensions={"sni_hostname": original.host},
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("redirect without location")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    raise ValueError("company page is not HTML")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise ValueError("company page is too large")
                return FetchedCompanyPage(
                    url=current_url, html=body.decode(response.encoding or "utf-8", errors="replace"),
                )
    raise ValueError("too many redirects")


def _assert_public_network_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        raise ValueError("unsafe company URL")
    if _is_excluded_host(host.lower()) or _is_non_public_literal_ip(host.lower()):
        raise ValueError("unsafe company host")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("unsafe company port")
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("company host did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError("company host resolved to a private address")
    return addresses[0][4][0]
