from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import NormalizedJob, SourceAdapter


ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_WEB_ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"
STORY_HITS_PER_PAGE = 20
COMMENT_HITS_PER_PAGE = 1000

MONTHLY_HIRING_TITLE_PATTERN = re.compile(
    r"^ask hn:\s+who(?:'s| is) hiring\?\s+\([^)]+\)$",
    re.IGNORECASE,
)
AI_KEYWORD_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|llm|agentic|rag|data science|data scientist|computer vision|nlp)\b",
    re.IGNORECASE,
)
CONTACT_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https?://t\.me/[A-Z0-9_]{3,32}|\b(?:telegram|wechat|weixin|phone|contact)\b",
    re.IGNORECASE,
)


class HNWhoIsHiringAIAdapter(SourceAdapter):
    source_name = "hn_whoishiring_ai"

    def fetch(self) -> list[NormalizedJob]:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            story = _find_latest_story(client)
            if not story:
                return []

            story_id = _str(story.get("objectID"))
            story_title = _str(story.get("title")) or _str(story.get("story_title"))
            comments = _fetch_story_comments(client, story_id)

            jobs: list[NormalizedJob] = []
            seen: set[str] = set()
            for comment in comments:
                if not isinstance(comment, dict):
                    continue
                if _str(comment.get("parent_id")) != story_id:
                    continue

                description = _html_to_text(_str(comment.get("comment_text")))
                if not _is_relevant(description):
                    continue

                source_job_id = _str(comment.get("objectID"))
                if not source_job_id or source_job_id in seen:
                    continue

                company, title, location = _parse_header(description)
                jobs.append(
                    NormalizedJob(
                        source_job_id=source_job_id,
                        canonical_url=HN_WEB_ITEM_URL.format(item_id=source_job_id),
                        title=title,
                        company=company,
                        location=location,
                        remote_type="remote" if "remote" in description.lower() else "unknown",
                        employment_type="unknown",
                        description=description[:4000],
                        posted_at=_parse_hn_time(comment.get("created_at_i")),
                        raw_payload={
                            "site": "hn_whoishiring_ai",
                            "story_id": story_id,
                            "story_title": _str(comment.get("story_title")) or story_title,
                            "story_url": HN_WEB_ITEM_URL.format(item_id=story_id),
                            "company_url": "",
                        },
                    )
                )
                seen.add(source_job_id)

        return jobs[:80]


def _find_latest_story(client: httpx.Client) -> dict[str, Any]:
    response = client.get(
        ALGOLIA_SEARCH_URL,
        params={"query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": STORY_HITS_PER_PAGE},
    )
    response.raise_for_status()
    hits = (response.json() or {}).get("hits") or []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        title = _str(hit.get("title")) or _str(hit.get("story_title"))
        if MONTHLY_HIRING_TITLE_PATTERN.search(title):
            return hit
    return {}


def _fetch_story_comments(client: httpx.Client, story_id: str) -> list[dict[str, Any]]:
    if not story_id:
        return []
    response = client.get(
        ALGOLIA_SEARCH_URL,
        params={
            "tags": f"comment,story_{story_id}",
            "numericFilters": f"parent_id={story_id}",
            "hitsPerPage": COMMENT_HITS_PER_PAGE,
        },
    )
    response.raise_for_status()
    hits = (response.json() or {}).get("hits") or []
    return [hit for hit in hits if isinstance(hit, dict)]


def _is_relevant(description: str) -> bool:
    return bool(AI_KEYWORD_PATTERN.search(description) and CONTACT_PATTERN.search(description))


def _parse_header(description: str) -> tuple[str, str, str]:
    first_line = description.splitlines()[0] if description else ""
    parts = [part.strip() for part in re.split(r"\s+\|\s+", first_line) if part.strip()]
    company = parts[0] if parts else ""
    title = parts[1] if len(parts) > 1 else "AI Hiring Lead"
    location = parts[2] if len(parts) > 2 else ""
    return company[:255], title[:255], location[:255]


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return "\n".join(line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip())


def _parse_hn_time(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)


def _str(value: Any) -> str:
    return str(value or "").strip()
