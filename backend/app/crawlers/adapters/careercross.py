from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


CAREERCROSS_KAIGAI_URL = "https://www.careercross.com/kaigai"
CAREERCROSS_HOME = "https://www.careercross.com"


class CareerCrossAdapter(SourceAdapter):
    source_name = "careercross"

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        html = fetch_html(CAREERCROSS_KAIGAI_URL)
        soup, _ = soup_links(html)
        listing_urls = _listing_urls(soup)

        for parsed in _parse_jobs(soup, CAREERCROSS_KAIGAI_URL):
            if parsed.canonical_url in seen:
                continue
            jobs.append(parsed)
            seen.add(parsed.canonical_url)

        for listing_url in listing_urls:
            if listing_url == CAREERCROSS_KAIGAI_URL:
                continue
            try:
                listing_html = fetch_html(listing_url)
            except Exception:  # noqa: BLE001
                continue
            listing_soup, _ = soup_links(listing_html)
            for parsed in _parse_jobs(listing_soup, listing_url):
                if parsed.canonical_url in seen:
                    continue
                jobs.append(parsed)
                seen.add(parsed.canonical_url)

        return jobs


def _listing_urls(soup) -> list[str]:
    urls = {CAREERCROSS_KAIGAI_URL}
    for link in soup.select("a[href*='/job-search/specialty-']"):
        href = str(link.get("href") or "").strip()
        if not href:
            continue
        urls.add(_strip_query(urljoin(CAREERCROSS_HOME, href)))
    return sorted(urls)


def _parse_jobs(soup, listing_url: str) -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []

    for link in soup.select("a[href*='/job/detail-']"):
        parsed = _parse_job_link(link, listing_url)
        if parsed is not None:
            jobs.append(parsed)

    return jobs


def _parse_job_link(link, listing_url: str) -> NormalizedJob | None:
    href = str(link.get("href") or "").strip()
    source_job_id = _extract_job_id(href)
    if not href or not source_job_id:
        return None

    canonical_url = _strip_query(urljoin(CAREERCROSS_HOME, href))
    title = _clean_text(str(link.get("title") or "") or link.get_text(" ", strip=True))
    if not title:
        return None

    container = link.find_parent(class_=re.compile(r"result-job-box"))
    company = _field_value(container, "採用企業") if container else ""
    location = _field_value(container, "勤務地") if container else ""
    employment_type = _field_value(container, "雇用形態") if container else "unknown"
    card_text = _clean_text(container.get_text(" ", strip=True)) if container else title

    return NormalizedJob(
        source_job_id=source_job_id,
        canonical_url=canonical_url,
        title=title[:180],
        company=company,
        location=location or "Japan",
        remote_type="remote" if "remote" in card_text.lower() or "リモート" in card_text else "unknown",
        employment_type=employment_type or "unknown",
        description=card_text[:4000],
        raw_payload={"site": "careercross", "listing_url": listing_url},
    )


def _field_value(container, label: str) -> str:
    if container is None:
        return ""
    for cell in container.select("td"):
        if _clean_text(cell.get_text(" ", strip=True)) != label:
            continue
        value_cell = cell.find_next_sibling("td")
        if value_cell is None:
            return ""
        return _clean_text(value_cell.get_text(" ", strip=True))
    return ""


def _strip_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _extract_job_id(href: str) -> str:
    match = re.search(r"/job/detail-(\d+)", href)
    return match.group(1) if match else ""


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
