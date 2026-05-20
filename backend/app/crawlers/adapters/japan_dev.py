from __future__ import annotations

from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class JapanDevAdapter(SourceAdapter):
    source_name = "japan_dev"

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://japan-dev.com/jobs"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for row in soup.select(".job-item"):
            title_el = row.select_one("a.job-item__title[href]")
            if not title_el:
                continue

            href = str(title_el.get("href") or "").strip()
            canonical_url = urljoin("https://japan-dev.com", href)
            title = " ".join(title_el.get_text(" ", strip=True).split())
            if not href or not title or canonical_url in seen:
                continue

            company, description = _parse_company_and_description(row)
            location = _parse_location(row)
            tags = _parse_tags(row)

            jobs.append(
                NormalizedJob(
                    source_job_id=href.strip("/"),
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in " ".join(tags).lower() else "unknown",
                    employment_type="unknown",
                    description=description,
                    posted_at=None,
                    raw_payload={"site": "japan_dev", "display_tags": tags},
                )
            )
            seen.add(canonical_url)

        return jobs


def _parse_company_and_description(row) -> tuple[str, str]:
    contract_el = row.select_one(".job-item__contract-type")
    text = " ".join(contract_el.get_text(" ", strip=True).split()) if contract_el else ""
    if not text:
        return "", ""

    parts = [part.strip() for part in text.split("・", 1)]
    if len(parts) == 2:
        return parts[0], parts[1][:4000]
    return parts[0], text[:4000]


def _parse_location(row) -> str:
    for item in row.select(".job__tag-desc"):
        text = " ".join(item.get_text(" ", strip=True).split())
        if text and "¥" not in text:
            return text
    return ""


def _parse_tags(row) -> list[str]:
    tags: list[str] = []
    for item in row.select(".job-top-tag-list__job-top-tag"):
        text = " ".join(item.get_text(" ", strip=True).split())
        if text and text not in tags:
            tags.append(text)
    return tags[:8]
