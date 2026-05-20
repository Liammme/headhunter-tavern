from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class GaijinPotAdapter(SourceAdapter):
    source_name = "gaijinpot"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://jobs.gaijinpot.com/en/job")
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href*='/en/job/']"):
            href = str(link.get("href") or "").strip()
            title = _clean_text(link.get_text(" ", strip=True))
            source_job_id = _extract_job_id(href)
            if not href or not title or not source_job_id:
                continue

            canonical_url = urljoin("https://jobs.gaijinpot.com", href)
            if canonical_url in seen:
                continue

            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    location="Japan",
                    remote_type="remote" if "remote" in title.lower() or "リモート" in title else "unknown",
                    employment_type="unknown",
                    description=title,
                    raw_payload={"site": "gaijinpot"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _extract_job_id(href: str) -> str:
    match = re.search(r"/en/job/(\d+)", href)
    return match.group(1) if match else ""


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
