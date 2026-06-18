from __future__ import annotations

from dataclasses import dataclass
import json
import re
from urllib.parse import unquote, urljoin, urlsplit

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


BASE_URL = "https://bonjour.bio"
LISTING_URL = f"{BASE_URL}/jobs-mapping/jobs"


@dataclass(frozen=True)
class _ListingJob:
    source_job_id: str
    canonical_url: str
    title: str
    company: str
    location: str
    team_slug: str
    team_url: str
    row_description: str


class BonjourBioAdapter(SourceAdapter):
    source_name = "bonjour_bio"

    def fetch(self) -> list[NormalizedJob]:
        html = fetch_html(LISTING_URL)
        soup, _ = soup_links(html)
        embedded_descriptions = _parse_embedded_descriptions(html)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for item in _parse_listing_jobs(soup):
            if item.canonical_url in seen:
                continue

            description = embedded_descriptions.get(item.source_job_id) or item.row_description

            jobs.append(
                NormalizedJob(
                    source_job_id=item.source_job_id,
                    canonical_url=item.canonical_url,
                    title=item.title,
                    company=item.company,
                    location=item.location,
                    remote_type="remote" if "remote" in item.location.lower() or "远程" in item.location else "unknown",
                    employment_type="unknown",
                    description=description[:4000],
                    raw_payload={
                        "site": "bonjour_bio",
                        "team_slug": item.team_slug,
                        "team_url": item.team_url,
                        "company_url": "",
                    },
                )
            )
            seen.add(item.canonical_url)

        return jobs[:100]


def _parse_listing_jobs(soup) -> list[_ListingJob]:
    items: list[_ListingJob] = []
    for row in soup.select(".jp-job-row"):
        job_anchor = row.select_one("a.jp-job-cover[href*='/jobs-mapping/jobs/']")
        if not job_anchor:
            continue

        href = str(job_anchor.get("href") or "").strip()
        canonical_url = urljoin(BASE_URL, href)
        source_job_id = _last_path_part(href)
        if not canonical_url or not source_job_id:
            continue

        aria_label = str(job_anchor.get("aria-label") or "")
        title = _node_text(row.select_one(".jp-role-title")) or _parse_title_from_label(aria_label)
        company = _node_text(row.select_one(".jp-team-name")) or _parse_company_from_label(aria_label)
        if not title:
            continue

        team_anchor = row.select_one("a.jp-team[href*='/jobs-mapping/team/']")
        team_href = str(team_anchor.get("href") or "").strip() if team_anchor else ""
        team_url = urljoin(BASE_URL, team_href) if team_href else ""
        team_slug = _last_path_part(team_href)

        metas = [_node_text(node) for node in row.select(".jp-meta .jp-loc")]
        location = " / ".join(_dedupe(value for value in metas if value))
        row_description = _node_text(row)

        items.append(
            _ListingJob(
                source_job_id=source_job_id,
                canonical_url=canonical_url,
                title=title,
                company=company,
                location=location,
                team_slug=team_slug,
                team_url=team_url,
                row_description=row_description,
            )
        )
    return items


def _parse_embedded_descriptions(html: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    pattern = re.compile(
        r'\\"id\\":\\"(?P<id>[^"\\]+)\\",\\"teamSlug\\":\\"(?P<team>[^"\\]*)\\"'
        r'.*?\\"descriptionMarkdown\\":\\"(?P<desc>(?:\\\\.|[^\\"])*)\\"',
        re.DOTALL,
    )
    for match in pattern.finditer(html or ""):
        job_id = match.group("id").strip()
        description = _decode_embedded_text(match.group("desc")).strip()
        if job_id and description:
            descriptions[job_id] = description
    return descriptions


def _decode_embedded_text(value: str) -> str:
    try:
        decoded = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        decoded = value
    return decoded.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")


def _node_text(node) -> str:
    if not node:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def _parse_title_from_label(value: str) -> str:
    match = re.search(r"的\s*(.+?)\s*职位", value or "")
    return " ".join(match.group(1).split()) if match else ""


def _parse_company_from_label(value: str) -> str:
    match = re.search(r"查看\s*(.+?)\s*的", value or "")
    return " ".join(match.group(1).split()) if match else ""


def _last_path_part(href: str) -> str:
    path = urlsplit(href or "").path.rstrip("/")
    if not path:
        return ""
    return unquote(path.rsplit("/", 1)[-1]).strip()


def _dedupe(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result
