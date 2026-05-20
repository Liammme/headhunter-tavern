from __future__ import annotations

import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


class GreenJapanAdapter(SourceAdapter):
    source_name = "green_japan"

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://www.green-japan.com/search_key/01"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for link in soup.select("a[href*='/company/'][href*='/job/']"):
            href = str(link.get("href") or "").strip()
            canonical_url = urljoin("https://www.green-japan.com", href)
            text = _clean_text(link.get_text(" ", strip=True))
            if not href or not text or canonical_url in seen:
                continue

            jobs.append(
                NormalizedJob(
                    source_job_id=href.strip("/"),
                    canonical_url=canonical_url,
                    title=_parse_title(text),
                    company=_parse_company(text),
                    location=_parse_location(text),
                    remote_type="remote" if "リモート" in text else "unknown",
                    employment_type="unknown",
                    description=text[:4000],
                    posted_at=None,
                    raw_payload={"site": "green_japan"},
                )
            )
            seen.add(canonical_url)

        return jobs


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())


def _parse_company(text: str) -> str:
    match = re.match(r"(.+?)\s+\d+\s*人\b", text)
    if match:
        return match.group(1).strip()
    return text[:80].strip()


def _parse_title(text: str) -> str:
    role_match = re.search(
        r"((?:リード|シニア|バックエンド|フロントエンド|ソフトウェア|システム開発|AI|機械学習|"
        r"データ|インフラ|SRE|DevOps|WEB|Web)?"
        r"(?:エンジニア|ディレクター|マネージャー|デザイナー|マーケター|コンサルタント|"
        r"カスタマーサクセス|営業|PM|PdM))",
        text,
        re.IGNORECASE,
    )
    if role_match:
        return role_match.group(1).strip()

    without_company = re.sub(r"^.+?\s+\d+\s*人\b", "", text).strip()
    without_founded = re.sub(r"^\d{4}年\s+設立\s*", "", without_company).strip()
    return without_founded[:120].strip() or text[:120].strip()


def _parse_location(text: str) -> str:
    if "フルリモート" in text:
        return "フルリモート"

    locations = [
        "リモート",
        "東京都",
        "神奈川県",
        "大阪府",
        "京都府",
        "福岡県",
        "北海道",
        "愛知県",
        "兵庫県",
        "埼玉県",
        "千葉県",
    ]
    found = [location for location in locations if location in text]
    return ", ".join(found[:3])
