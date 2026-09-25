from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import NormalizedJob, SourceAdapter


MAX_TOPICS = 30
AI_JOB_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|deep learning|pytorch|llm|agentic|rag|data science|data scientist|computer vision|nlp|robotics|ros2?|autonom(?:y|ous)|reinforcement learning)\b",
    re.IGNORECASE,
)
CANDIDATE_POST_PATTERN = re.compile(
    r"\b(?:looking for work|looking for a job|available for hire|seeking work|seeking employment|currently looking for .* position)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DiscourseJobSource:
    source_name: str
    base_url: str
    category_path: str

    @property
    def category_json_url(self) -> str:
        return f"{self.base_url}{self.category_path}.json"

    @property
    def category_url(self) -> str:
        return f"{self.base_url}{self.category_path}"

    @property
    def feed_url(self) -> str:
        return f"{self.category_url}.rss"


OPEN_ROBOTICS_SOURCE = DiscourseJobSource(
    source_name="open_robotics_jobs",
    base_url="https://discourse.openrobotics.org",
    category_path="/c/jobs/15",
)
PYTORCH_SOURCE = DiscourseJobSource(
    source_name="pytorch_jobs",
    base_url="https://discuss.pytorch.org",
    category_path="/c/jobs/24",
)


class OpenRoboticsJobsAdapter(SourceAdapter):
    source_name = OPEN_ROBOTICS_SOURCE.source_name

    def fetch(self) -> list[NormalizedJob]:
        return _fetch_discourse_jobs(OPEN_ROBOTICS_SOURCE)


class PyTorchJobsAdapter(SourceAdapter):
    source_name = PYTORCH_SOURCE.source_name

    def fetch(self) -> list[NormalizedJob]:
        return _fetch_discourse_jobs(PYTORCH_SOURCE)


def _fetch_discourse_jobs(source: DiscourseJobSource) -> list[NormalizedJob]:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml, application/xml"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(source.feed_url)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()
        for item in root.findall("./channel/item")[:MAX_TOPICS]:
            title = _xml_text(item, "title")
            canonical_url = _xml_text(item, "link")
            description_html = _xml_text(item, "description")
            if not title or not canonical_url or _is_non_job_topic(title):
                continue
            description = "\n".join(value for value in (title, _html_to_text(description_html)) if value)
            if not _is_relevant_hiring_post(description):
                continue
            if canonical_url in seen:
                continue

            path_parts = [part for part in urlsplit(canonical_url).path.split("/") if part]
            topic_id = path_parts[-1] if path_parts else canonical_url
            slug = path_parts[-2] if len(path_parts) >= 2 else topic_id
            company, location = _parse_company_and_location(title)
            jobs.append(
                NormalizedJob(
                    source_job_id=topic_id,
                    canonical_url=canonical_url,
                    title=title[:255],
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in description.lower() else "unknown",
                    employment_type="unknown",
                    description=description[:4000],
                    posted_at=_parse_datetime(_xml_text(item, "pubDate")),
                    raw_payload={
                        "site": source.source_name,
                        "topic_slug": slug,
                        "category_url": source.category_url,
                        "company_url": _extract_company_url(description_html, source=source),
                    },
                )
            )
            seen.add(canonical_url)

    return jobs[:80]


def _is_relevant_hiring_post(description: str) -> bool:
    if CANDIDATE_POST_PATTERN.search(description):
        return False
    return bool(AI_JOB_PATTERN.search(description))


def _is_non_job_topic(title: str) -> bool:
    normalized = title.strip().lower()
    return normalized.startswith("about the ") or normalized.startswith("category ")


def _parse_company_and_location(title: str) -> tuple[str, str]:
    parts = [part.strip() for part in re.split(r"\s+\|\s+", title) if part.strip()]
    if len(parts) >= 2:
        company = parts[0]
        location = next((part for part in parts[1:] if _looks_like_location(part)), "")
        return company[:255], location[:255]

    pieces = [part.strip() for part in re.split(r"\s+[–—-]\s+", title, maxsplit=1) if part.strip()]
    company = pieces[0] if len(pieces) > 1 and not _starts_like_generic_request(pieces[0]) else ""
    return company[:255], ""


def _looks_like_location(value: str) -> bool:
    return bool(re.search(r"\b(remote|onsite|on-site|hybrid|usa|us|uk|eu|europe|germany|france|spain|japan|tokyo|nyc|new york|bay area|san francisco|london|berlin|munich)\b", value, re.IGNORECASE))


def _starts_like_generic_request(value: str) -> bool:
    return bool(re.match(r"^(seeking|looking|hiring|wanted|job|phd|internship)\b", value.strip(), re.IGNORECASE))


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return "\n".join(line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip())


def _extract_company_url(value: str, *, source: DiscourseJobSource) -> str:
    excluded_hosts = {
        urlsplit(source.base_url).hostname,
        "linkedin.com",
        "lnkd.in",
        "workday.com",
        "myworkdayjobs.com",
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "indeed.com",
    }
    soup = BeautifulSoup(value or "", "html.parser")
    for anchor in soup.select("a[href]"):
        # An arbitrary outbound link can be a vendor or an article, not the employer.
        label = anchor.get_text(" ", strip=True).lower()
        if label not in {"company website", "our website", "visit our website", "官网", "公司官网"}:
            continue
        href = anchor.get("href", "").strip()
        parsed = urlsplit(href)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if parsed.scheme not in {"http", "https"} or not host:
            continue
        if any(host == excluded or host.endswith(f".{excluded}") for excluded in excluded_hosts if excluded):
            continue
        return href
    return ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _xml_text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    return (node.text or "").strip() if node is not None else ""
