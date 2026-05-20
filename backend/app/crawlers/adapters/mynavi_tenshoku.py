from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class MynaviTenshokuAdapter(SourceAdapter):
    source_name = "mynavi_tenshoku"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://tenshoku.mynavi.jp/list/")
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href*='jobinfo-']"):
            href = str(link.get("href") or "").strip()
            title = _clean_text(link.get_text(" ", strip=True))
            source_job_id = _extract_source_id(href)
            if not href or not title or not source_job_id or title == "求人詳細を見る":
                continue
            if re.search(r"/(?:adv\d+|msg)/?$", href):
                continue

            canonical_url = urljoin("https://tenshoku.mynavi.jp", href)
            if canonical_url in seen:
                continue

            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    location="Japan",
                    remote_type="remote" if "リモート" in title or "在宅" in title else "unknown",
                    employment_type="unknown",
                    description=title,
                    raw_payload={"site": "mynavi_tenshoku"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _extract_source_id(href: str) -> str:
    match = re.search(r"(jobinfo-[^/?#]+)", href)
    return match.group(1).strip("/") if match else ""


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
