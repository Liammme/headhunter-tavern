from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class WantedlyAdapter(SourceAdapter):
    source_name = "wantedly"

    @staticmethod
    def _extract_detail(detail_url: str) -> tuple[str, str]:
        try:
            html = fetch_html(detail_url, timeout=25)
            soup, _ = soup_links(html)
        except Exception:  # noqa: BLE001
            return "", ""

        company = ""
        company_node = soup.select_one("a[href*='/companies/'], [data-company-name], .company-name")
        if company_node:
            company = _clean_text(company_node.get_text(" ", strip=True))

        description = ""
        for selector in (
            "[itemprop='description']",
            ".project-description",
            ".wanted-project-description",
            "article",
            "main",
        ):
            node = soup.select_one(selector)
            if not node:
                continue
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                description = text[:4000]
                break
        return company, description

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html("https://www.wantedly.com/projects")
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href*='/projects/']"):
            href = str(link.get("href") or "").strip()
            title = _clean_text(link.get_text(" ", strip=True))
            source_job_id = _extract_project_id(href)
            if not href or not title or not source_job_id:
                continue

            canonical_url = f"https://www.wantedly.com/projects/{source_job_id}"
            if canonical_url in seen:
                continue

            detail_company, detail_description = self._extract_detail(canonical_url)

            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title[:180],
                    company=detail_company,
                    location="Japan",
                    remote_type="remote" if "リモート" in title or "在宅" in title else "unknown",
                    employment_type="unknown",
                    description=(detail_description or title)[:4000],
                    raw_payload={"site": "wantedly"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _extract_project_id(href: str) -> str:
    match = re.search(r"/projects/(\d+)", href)
    return match.group(1) if match else ""


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
