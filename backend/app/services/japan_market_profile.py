from __future__ import annotations

import re

from app.crawlers.base import NormalizedJob
from app.services.market_intelligence_fact_extractor import ExtractedMarketIntelligenceFact

JAPAN_RECRUITING_MARKET_PROFILE = "japan_recruiting_market_v1"

SOURCE_FAMILIES = {
    "withb": "bilingual / international",
    "gaijinpot": "bilingual / international",
    "yolo_japan": "bilingual / international",
    "japan_dev": "tech specialist",
    "green_japan": "tech / startup",
    "wantedly": "startup / culture-fit",
    "mynavi_tenshoku": "general job board",
    "en_tenshoku": "general job board",
    "type_jp": "tech / professional",
    "daijob": "bilingual / international",
}


def build_japan_fact_profile(job: NormalizedJob, extracted: ExtractedMarketIntelligenceFact) -> dict:
    text = _combined_text(job)
    salary_type = _salary_type(text)
    return {
        "report_profile": JAPAN_RECRUITING_MARKET_PROFILE,
        "source_family": _source_family(job),
        "location_signal": _location_signal(job.location, text),
        "remote_policy": _remote_policy(job.remote_type, text),
        "employment_type": _employment_type(job.employment_type, text),
        "experience_level": _experience_level(extracted.seniority, text),
        "language_requirement": _language_requirement(text),
        "salary_disclosure": "disclosed" if extracted.salary_signal != "unknown" or salary_type != "unknown" else "undisclosed",
        "salary_type": salary_type,
        "industry_hint": _industry_hint(text),
    }


def _combined_text(job: NormalizedJob) -> str:
    return " ".join([job.title or "", job.company or "", job.location or "", job.employment_type or "", job.description or ""]).lower()


def _source_family(job: NormalizedJob) -> str:
    source = ""
    if isinstance(job.raw_payload, dict):
        source = str(job.raw_payload.get("site") or "").strip().lower()
    return SOURCE_FAMILIES.get(source, "unknown")


def _location_signal(location: str, text: str) -> str:
    value = f"{location or ''} {text}".lower()
    if any(token in value for token in ("東京", "東京都", "tokyo")):
        return "tokyo"
    if any(token in value for token in ("大阪", "osaka")):
        return "osaka"
    if any(token in value for token in ("京都", "kyoto")):
        return "kyoto"
    if any(token in value for token in ("福岡", "fukuoka")):
        return "fukuoka"
    if any(token in value for token in ("名古屋", "nagoya")):
        return "nagoya"
    if any(token in value for token in ("全国", "remote", "リモート", "在宅")):
        return "remote / nationwide"
    if location.strip():
        return "other japan"
    return "unknown"


def _remote_policy(remote_type: str, text: str) -> str:
    value = f"{remote_type or ''} {text}".lower()
    if any(token in value for token in ("hybrid", "ハイブリッド", "一部リモート")):
        return "hybrid"
    if any(token in value for token in ("remote", "リモート", "在宅", "フルリモート")):
        return "remote"
    if any(token in value for token in ("onsite", "出社", "常駐")):
        return "onsite"
    return "unknown"


def _employment_type(employment_type: str, text: str) -> str:
    value = f"{employment_type or ''} {text}".lower()
    if any(token in value for token in ("正社員", "full time", "full-time", "permanent")):
        return "permanent"
    if any(token in value for token in ("契約社員", "contract")):
        return "contract"
    if any(token in value for token in ("派遣", "temporary staffing")):
        return "dispatch"
    if any(token in value for token in ("アルバイト", "パート", "part time", "part-time")):
        return "part_time"
    if any(token in value for token in ("インターン", "intern")):
        return "internship"
    if any(token in value for token in ("業務委託", "freelance", "outsourcing")):
        return "outsourced / freelance"
    return "unknown"


def _experience_level(seniority: str, text: str) -> str:
    if any(token in text for token in ("未経験", "未経験ok", "未経験歓迎", "no experience", "inexperienced")):
        return "entry / inexperienced"
    if seniority in {"senior", "lead", "principal"}:
        return "senior"
    if seniority in {"junior", "entry"}:
        return "entry / inexperienced"
    if any(token in text for token in ("manager", "マネージャー", "管理職", "責任者")):
        return "management"
    if any(token in text for token in ("3年以上", "5年以上", "mid-level", "middle")):
        return "mid-level"
    return "unspecified"


def _language_requirement(text: str) -> str:
    has_japanese = any(token in text for token in ("日本語", "jlpt", " n1", " n2", "ネイティブ"))
    has_english = any(token in text for token in ("英語", "english", "toeic", "business english"))
    if has_japanese and has_english:
        return "japanese + english"
    if has_japanese:
        return "japanese_required"
    if has_english:
        return "english_signal"
    if any(token in text for token in ("外国人", "visa", "ビザ", "グローバル")):
        return "international_friendly"
    return "unknown"


def _salary_type(text: str) -> str:
    if any(token in text for token in ("年収", "年俸", "annual")):
        return "annual"
    if any(token in text for token in ("月給", "monthly")):
        return "monthly"
    if any(token in text for token in ("時給", "hourly")):
        return "hourly"
    if re.search(r"\b(jpy|¥|円|万円)\b", text):
        return "amount_only"
    return "unknown"


def _industry_hint(text: str) -> str:
    if any(token in text for token in ("web3", "blockchain", "crypto", "暗号資産", "仮想通貨", "ウォレット")):
        return "web3 / crypto"
    if any(token in text for token in ("生成ai", "人工知能", "machine learning", "llm", " ai ", " ai/")):
        return "ai"
    if any(token in text for token in ("saas", "cloud", "クラウド")):
        return "saas / cloud"
    if any(token in text for token in ("fintech", "金融", "決済", "payment")):
        return "finance / payment"
    if any(token in text for token in ("game", "ゲーム")):
        return "game"
    if any(token in text for token in ("製造", "メーカー", "manufacturing")):
        return "manufacturing"
    return "other"
