from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import NormalizedJob, SourceAdapter


MAX_TOPICS = 30
AI_JOB_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|deep learning|pytorch|llm|agentic|rag|data science|data scientist|computer vision|nlp|robotics|ros2?|autonom(?:y|ous)|reinforcement learning)\b",
    re.IGNORECASE,
)
DIRECT_CONTACT_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"\b[A-Z0-9._%+-]+\s*(?:\(|\[)?\s*at\s*(?:\)|\])?\s*"
    r"[A-Z0-9.-]+\s*(?:\(|\[)?\s*dot\s*(?:\)|\])?\s*[A-Z]{2,}\b|"
    r"https?://(?:t\.me|telegram\.me|discord\.gg)/[^\s<>()]+|"
    r"\b(?:telegram|wechat|weixin|whatsapp|discord)\s*[:：]\s*[A-Z0-9@_.#-]{3,40}|"
    r"\b(?:phone|tel|mobile)\s*[:：]?\s*[+＋]?\d[\d\s().-]{6,}\d",
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
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(source.category_json_url)
        response.raise_for_status()
        topics = ((response.json() or {}).get("topic_list") or {}).get("topics") or []

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()
        for topic in topics[:MAX_TOPICS]:
            if not isinstance(topic, dict):
                continue

            topic_id = _str(topic.get("id"))
            slug = _str(topic.get("slug"))
            title = _str(topic.get("title"))
            if not topic_id or not slug or not title or _is_non_job_topic(title):
                continue

            detail_url = f"{source.base_url}/t/{slug}/{topic_id}.json"
            detail_response = client.get(detail_url)
            detail_response.raise_for_status()
            payload = detail_response.json() or {}
            description = _description_from_topic(title, payload)
            if not _is_relevant_hiring_post(description):
                continue
            if topic_id in seen:
                continue

            canonical_url = f"{source.base_url}/t/{slug}/{topic_id}"
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
                    posted_at=_parse_datetime(_str(topic.get("created_at"))),
                    raw_payload={
                        "site": source.source_name,
                        "topic_slug": slug,
                        "category_url": source.category_url,
                        "company_url": "",
                    },
                )
            )
            seen.add(topic_id)

    return jobs[:80]


def _description_from_topic(title: str, payload: dict[str, Any]) -> str:
    posts = (payload.get("post_stream") or {}).get("posts") or []
    first_post = posts[0] if posts and isinstance(posts[0], dict) else {}
    body = _str(first_post.get("cooked"))
    text = _html_to_text(body)
    return "\n".join(value for value in (title, text) if value)


def _is_relevant_hiring_post(description: str) -> bool:
    if CANDIDATE_POST_PATTERN.search(description):
        return False
    return bool(AI_JOB_PATTERN.search(description) and DIRECT_CONTACT_PATTERN.search(description))


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


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _str(value: Any) -> str:
    return str(value or "").strip()
