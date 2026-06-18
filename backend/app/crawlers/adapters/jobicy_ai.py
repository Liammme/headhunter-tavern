from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import NormalizedJob, SourceAdapter


API_URL = "https://jobicy.com/api/v2/remote-jobs?count=100"
TITLE_AI_KEYWORD_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|llm|rag|data scientist|data science|computer vision|nlp|prompt engineer)\b",
    re.IGNORECASE,
)


class JobicyAIAdapter(SourceAdapter):
    source_name = "jobicy_ai"

    def fetch(self) -> list[NormalizedJob]:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            response = client.get(API_URL)
            response.raise_for_status()
            payload = response.json()

        jobs = payload.get("jobs") if isinstance(payload, dict) else []
        if not isinstance(jobs, list):
            return []

        normalized: list[NormalizedJob] = []
        seen: set[str] = set()
        for item in jobs:
            if not isinstance(item, dict):
                continue

            title = _str(item.get("jobTitle"))
            description = _html_to_text(_str(item.get("jobDescription")))
            if not title or not _is_ai_related(title):
                continue

            canonical_url = _str(item.get("url"))
            source_job_id = _str(item.get("id")) or _str(item.get("jobSlug")) or canonical_url
            if not canonical_url or canonical_url in seen:
                continue

            normalized.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    company=_str(item.get("companyName")),
                    location=_str(item.get("jobGeo")),
                    remote_type="remote",
                    employment_type=_join_values(item.get("jobType")) or "unknown",
                    description=description[:4000],
                    posted_at=_parse_datetime(_str(item.get("pubDate"))),
                    raw_payload={
                        "site": "jobicy_ai",
                        "job_slug": _str(item.get("jobSlug")),
                        "company_url": "",
                    },
                )
            )
            seen.add(canonical_url)

        return normalized[:80]


def _is_ai_related(title: str) -> bool:
    return bool(TITLE_AI_KEYWORD_PATTERN.search(title))


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def _join_values(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_str(item) for item in value if _str(item))
    return _str(value)


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
