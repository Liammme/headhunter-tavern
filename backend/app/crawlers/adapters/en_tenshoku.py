from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class EnTenshokuAdapter(SourceAdapter):
    source_name = "en_tenshoku"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://employment.en-japan.com/list_new_search/")
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href^='/desc_']"):
            href = str(link.get("href") or "").strip()
            title = _clean_text(link.get_text(" ", strip=True))
            source_job_id = _extract_job_id(href)
            if not href or not title or not source_job_id or title == "詳細へ":
                continue

            canonical_url = f"https://employment.en-japan.com/desc_{source_job_id}/"
            if canonical_url in seen:
                continue

            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    location="Japan",
                    remote_type="remote" if "リモート" in title or "テレワーク" in title or "在宅" in title else "unknown",
                    employment_type="unknown",
                    description=title,
                    raw_payload={"site": "en_tenshoku"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _extract_job_id(href: str) -> str:
    match = re.search(r"/desc_(\d+)/", href)
    return match.group(1) if match else ""


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
