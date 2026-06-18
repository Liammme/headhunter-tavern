from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urljoin, urlparse

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


CATEGORY_URLS = (
    "https://withb.co.jp/category/engineer/",
    "https://withb.co.jp/category/designer/",
    "https://withb.co.jp/category/marketing/",
    "https://withb.co.jp/category/risk_compliance/",
    "https://withb.co.jp/category/internalaudit/",
    "https://withb.co.jp/category/tresury_accounting/",
    "https://withb.co.jp/category/legal/",
    "https://withb.co.jp/category/sales/",
    "https://withb.co.jp/category/customersupport/",
    "https://withb.co.jp/category/businessdeveloper/",
    "https://withb.co.jp/category/pr/",
    "https://withb.co.jp/category/hr/",
    "https://withb.co.jp/category/projectmanager/",
    "https://withb.co.jp/category/generalaffairs/",
    "https://withb.co.jp/category/communitymanager/",
    "https://withb.co.jp/category/financialadministrator/",
    "https://withb.co.jp/category/cxo/",
    "https://withb.co.jp/category/localization_translator/",
    "https://withb.co.jp/category/businessplanning/",
    "https://withb.co.jp/category/consultant/",
    "https://withb.co.jp/category/writer/",
    "https://withb.co.jp/category/financialprofession/",
    "https://withb.co.jp/category/labor/",
    "https://withb.co.jp/category/gameproducer/",
    "https://withb.co.jp/category/%e3%82%aa%e3%83%bc%e3%83%97%e3%83%b3%e3%83%9d%e3%82%b8%e3%82%b7%e3%83%a7%e3%83%b3/",
    "https://withb.co.jp/category/dealer-trader-quant/",
    "https://withb.co.jp/category/others/",
)

_CATEGORY_LABELS = (
    "エンジニア",
    "デザイナー",
    "マーケティング",
    "リスク・コンプライアンス",
    "内部監査",
    "財務・経理",
    "リーガル",
    "セールス",
    "カスタマーサポート",
    "ビジネスデベロッパー",
    "広報・PR",
    "人事",
    "PM/PdM",
    "総務",
    "コミュニティマネージャー",
    "金融事務",
    "CxO／責任者",
    "経営企画",
    "コンサルタント",
    "ライター",
    "金融専門職",
    "労務",
    "ゲームプロデューサー",
    "ローカライズ／翻訳・通訳",
    "オープンポジション",
    "ディーラー",
    "その他",
)


class WithBAdapter(SourceAdapter):
    source_name = "withb"

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for category_url in CATEGORY_URLS:
            try:
                category_html = fetch_html(category_url)
            except Exception:  # noqa: BLE001
                continue
            category_soup, _ = soup_links(category_html)

            for page_url in _category_page_urls(category_url, category_soup):
                soup = category_soup
                if page_url != category_url:
                    try:
                        html = fetch_html(page_url)
                    except Exception:  # noqa: BLE001
                        continue
                    soup, _ = soup_links(html)

                for article in soup.select("article"):
                    parsed = _parse_article(article)
                    if parsed is None or parsed.canonical_url in seen:
                        continue
                    jobs.append(parsed)
                    seen.add(parsed.canonical_url)

        return jobs


def _category_page_urls(category_url: str, soup) -> list[str]:
    urls = {category_url}
    category_path = urlparse(category_url).path.rstrip("/")

    for link in soup.select("a[href]"):
        href = urljoin("https://withb.co.jp", str(link.get("href") or "").strip())
        path = urlparse(href).path.rstrip("/")
        if path.startswith(f"{category_path}/page/"):
            urls.add(href)

    return sorted(urls)


def _parse_article(article) -> NormalizedJob | None:
    link = article.select_one("a[href]")
    if not link:
        return None

    href = str(link.get("href") or "").strip()
    canonical_url = urljoin("https://withb.co.jp", href)
    if not re.search(r"withb\.co\.jp/\d+/?$", canonical_url):
        return None

    text = _clean_text(link.get_text(" ", strip=True))
    if not text:
        return None

    title, salary, posted_at, company = _parse_listing_text(text)
    if not title:
        return None

    detail_text = _extract_detail(canonical_url)
    description = detail_text or text

    return NormalizedJob(
        source_job_id=urlparse(canonical_url).path.strip("/"),
        canonical_url=canonical_url,
        title=title,
        company=company,
        location="Japan",
        remote_type="remote" if "リモート" in text else "unknown",
        employment_type="unknown",
        description=description[:4000],
        posted_at=posted_at,
        raw_payload={"site": "withb", "salary": salary},
    )


def _extract_detail(detail_url: str) -> str:
    try:
        html = fetch_html(detail_url, timeout=25)
        soup, _ = soup_links(html)
    except Exception:  # noqa: BLE001
        return ""

    for selector in ("article", ".entry-content", ".post-content", "main"):
        node = soup.select_one(selector)
        if not node:
            continue
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            return text[:4000]
    return ""


def _parse_listing_text(text: str) -> tuple[str, str, datetime | None, str]:
    normalized = _strip_category_label(text)
    salary = ""
    salary_match = re.search(r"給与：\s*(.+?)\s+(\d{4}\.\d{2}\.\d{2})\s+(.+)$", normalized)
    if salary_match:
        title = normalized[: salary_match.start()].strip()
        salary = salary_match.group(1).strip()
        posted_at = _parse_date(salary_match.group(2))
        company = salary_match.group(3).strip()
        return title, salary, posted_at, company

    date_match = re.search(r"(\d{4}\.\d{2}\.\d{2})\s+(.+)$", normalized)
    if date_match:
        title = normalized[: date_match.start()].strip()
        posted_at = _parse_date(date_match.group(1))
        company = date_match.group(2).strip()
        return title, salary, posted_at, company

    return normalized, salary, None, ""


def _strip_category_label(text: str) -> str:
    for label in _CATEGORY_LABELS:
        prefix = f"{label} "
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y.%m.%d")
    except ValueError:
        return None


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
