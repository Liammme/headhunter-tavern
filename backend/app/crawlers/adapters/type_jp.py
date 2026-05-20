from __future__ import annotations

from urllib.parse import parse_qs, urljoin, urlparse

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class TypeJpAdapter(SourceAdapter):
    source_name = "type_jp"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://type.jp/job/search/")
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href*='jobId=']"):
            href = str(link.get("href") or "").strip()
            title = _clean_text(link.get_text(" ", strip=True))
            source_job_id = _extract_job_id(href)
            if not href or not title or not source_job_id or title == "求人を見る":
                continue

            canonical_url = urljoin("https://type.jp", href)
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
                    raw_payload={"site": "type_jp"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _extract_job_id(href: str) -> str:
    query = parse_qs(urlparse(href).query)
    return (query.get("jobId") or [""])[0]


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
