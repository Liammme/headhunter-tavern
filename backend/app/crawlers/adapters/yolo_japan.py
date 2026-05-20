from __future__ import annotations

from collections.abc import Iterable

import httpx

from app.crawlers.base import NormalizedJob, SourceAdapter


class YoloJapanAdapter(SourceAdapter):
    source_name = "yolo_japan"

    def fetch(self) -> list[NormalizedJob]:
        payload = fetch_json("https://www.yolo-japan.com/en/recruit/job/ajax/list?order=new")
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for item in _iter_job_items(payload.get("jobData", {})):
            source_job_id = str(item.get("jobId") or item.get("id") or "").strip()
            title = _clean_text(str(item.get("title") or ""))
            if not source_job_id or not title:
                continue

            canonical_url = f"https://www.yolo-japan.com/en/recruit/job/details/{source_job_id}"
            if canonical_url in seen:
                continue

            location = _join_non_empty(item.get("prefecture"), item.get("city"))
            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    company=_clean_text(str(item.get("companyName") or "")),
                    location=location or "Japan",
                    remote_type="remote" if "remote" in title.lower() or "リモート" in title else "unknown",
                    employment_type=str(item.get("type") or "unknown"),
                    description=title,
                    raw_payload={"site": "yolo_japan"},
                )
            )
            seen.add(canonical_url)

        return jobs


def fetch_json(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}


def _iter_job_items(value) -> Iterable[dict]:
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_job_items(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, dict):
                yield child
            else:
                yield from _iter_job_items(child)


def _join_non_empty(*values) -> str:
    return ", ".join(_clean_text(str(value)) for value in values if _clean_text(str(value or "")))


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
