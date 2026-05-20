from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class DaijobAdapter(SourceAdapter):
    source_name = "daijob"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://www.daijob.com/en/jobs/search_result")
        soup, _ = soup_links(html)
        by_url: dict[str, list[str]] = {}

        for link in soup.select("a[href*='/jobs/detail/']"):
            href = str(link.get("href") or "").strip()
            text = _clean_text(link.get_text(" ", strip=True))
            if not href or not text:
                continue
            canonical_url = urljoin("https://www.daijob.com", href)
            by_url.setdefault(canonical_url, []).append(text)

        jobs: list[NormalizedJob] = []
        for canonical_url, texts in by_url.items():
            source_job_id = _extract_job_id(canonical_url)
            title = max(texts, key=len)
            company = _select_company(texts, title)
            if not source_job_id or not title:
                continue
            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title[:180],
                    company=company,
                    location="Japan",
                    remote_type="remote" if "remote" in title.lower() or "リモート" in title else "unknown",
                    employment_type="unknown",
                    description=" ".join(texts)[:4000],
                    raw_payload={"site": "daijob"},
                )
            )

        return jobs


def _extract_job_id(url: str) -> str:
    match = re.search(r"/jobs/detail/(\d+)", url)
    return match.group(1) if match else ""


def _parse_company(text: str) -> str:
    match = re.search(r"\[([^\]]+)\]", text)
    return match.group(1).strip() if match else ""


def _select_company(texts: list[str], title: str) -> str:
    ignored = {"View Full Listing", "Details"}
    candidates = [text for text in texts if text not in ignored and len(text) <= 80]
    if candidates:
        return candidates[0]
    return _parse_company(title)


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
