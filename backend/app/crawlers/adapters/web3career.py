from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from html import unescape
import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob
from app.crawlers.http_helpers import fetch_html, soup_links
from app.crawlers.base import SourceAdapter


class Web3CareerAdapter(SourceAdapter):
    source_name = "web3career"

    @staticmethod
    def _parse_posted_at(date_posted: str) -> datetime | None:
        raw = (date_posted or "").strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, fmt)
                if parsed.tzinfo:
                    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed
            except ValueError:
                continue
        return None

    def fetch(self):
        listing_url = "https://web3.career/"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        listing_links = _build_listing_links(soup)

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.get_text(strip=True)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                    continue

                title = unescape(str(item.get("title") or "")).strip()
                if not title:
                    continue

                org = item.get("hiringOrganization")
                company = ""
                company_url = ""
                if isinstance(org, dict):
                    company = unescape(str(org.get("name") or "")).strip()
                    company_url = str(org.get("url") or org.get("sameAs") or "").strip()

                date_posted = str(item.get("datePosted") or "").strip()
                posted_at = self._parse_posted_at(date_posted)
                source_job_id = hashlib.sha1(f"{title}|{company}|{date_posted}".encode("utf-8")).hexdigest()

                location = ""
                loc_req = item.get("applicantLocationRequirements")
                if isinstance(loc_req, dict):
                    location = unescape(str(loc_req.get("name") or "")).strip()
                if not location:
                    location = unescape(str(item.get("jobLocationType") or "")).strip()

                remote_type = "remote" if "telecommute" in location.lower() or "anywhere" in location.lower() else "unknown"
                employment = item.get("employmentType")
                if isinstance(employment, list):
                    employment_type = ",".join(str(x) for x in employment)
                else:
                    employment_type = str(employment or "unknown")

                canonical_url = str(item.get("url") or "").strip()
                if canonical_url:
                    canonical_url = urljoin("https://web3.career", canonical_url)
                else:
                    canonical_url = _resolve_listing_url(listing_links, title=title, company=company)

                jobs.append(
                    NormalizedJob(
                        source_job_id=source_job_id,
                        canonical_url=canonical_url,
                        title=title,
                        company=company,
                        location=location,
                        remote_type=remote_type,
                        employment_type=employment_type,
                        description=unescape(str(item.get("description") or "")).strip()[:4000],
                        posted_at=posted_at,
                        raw_payload={"site": "web3career", "company_url": company_url, "date_posted": date_posted},
                    )
                )

        return jobs[:80]


def _build_listing_links(soup) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not re.search(r"/\d+$", href):
            continue

        text = " ".join(anchor.get_text(" ", strip=True).split())
        if not text:
            continue

        canonical_url = urljoin("https://web3.career", href)
        links.append((_normalize_listing_text(text), canonical_url))
    return links


def _resolve_listing_url(listing_links: list[tuple[str, str]], *, title: str, company: str) -> str:
    normalized_title = _normalize_listing_text(title)
    normalized_company = _normalize_listing_text(company)
    for text, canonical_url in listing_links:
        if not text.startswith(normalized_title):
            continue
        if normalized_company and normalized_company not in text:
            continue
        return canonical_url
    return "https://web3.career/"


def _normalize_listing_text(value: str) -> str:
    return " ".join(value.lower().split())
