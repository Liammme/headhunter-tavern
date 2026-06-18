from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import NormalizedJob, SourceAdapter


API_URL = "https://remoteok.com/api?tags=ai"
EXPLICIT_AI_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|llm|agent|rag|data science|computer vision|nlp)\b|\.ai\b",
    re.IGNORECASE,
)
TECHNICAL_ROLE_PATTERN = re.compile(
    r"\b(engineer|developer|scientist|researcher|architect|analyst|data|product|backend|frontend|full[- ]stack|annotator|ml|technology|technical|cto)\b",
    re.IGNORECASE,
)


class RemoteOKAIAdapter(SourceAdapter):
    source_name = "remoteok_ai"

    def fetch(self) -> list[NormalizedJob]:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            response = client.get(API_URL)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list):
            return []

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()
        for item in payload:
            if not isinstance(item, dict) or not item.get("id"):
                continue

            title = _str(item.get("position"))
            canonical_url = _str(item.get("url"))
            if not title or not canonical_url or canonical_url in seen:
                continue

            tags = item.get("tags") if isinstance(item.get("tags"), list) else []
            description = _html_to_text(_str(item.get("description")))
            company = _str(item.get("company"))
            if not _is_ai_related(title, tags, company=company):
                continue
            apply_url = _str(item.get("apply_url"))

            jobs.append(
                NormalizedJob(
                    source_job_id=_str(item.get("id")),
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=_str(item.get("location")),
                    remote_type="remote",
                    employment_type="unknown",
                    description=description[:4000],
                    posted_at=_parse_datetime(_str(item.get("date"))),
                    raw_payload={
                        "site": "remoteok_ai",
                        "apply_url": apply_url,
                        "company_url": apply_url,
                        "tags": tags,
                    },
                )
            )
            seen.add(canonical_url)

        return jobs[:80]


def _is_ai_related(title: str, tags: list[Any], company: str = "") -> bool:
    tag_text = " ".join(_str(tag) for tag in tags)
    if EXPLICIT_AI_PATTERN.search(f"{title}\n{company}"):
        return True
    if not EXPLICIT_AI_PATTERN.search(tag_text):
        return False
    return bool(TECHNICAL_ROLE_PATTERN.search(title))


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


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
