from __future__ import annotations

from dataclasses import dataclass
import re

from app.models import Job


@dataclass(frozen=True)
class BdContactCandidate:
    contact_type: str
    contact_value: str
    confidence: str
    evidence_snippet: str


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
OBFUSCATED_EMAIL_PATTERN = re.compile(
    r"\b([A-Z0-9._%+-]+)\s*(?:\(|\[)?\s*at\s*(?:\)|\])?\s*"
    r"([A-Z0-9.-]+)\s*(?:\(|\[)?\s*dot\s*(?:\)|\])?\s*([A-Z]{2,})\b",
    re.IGNORECASE,
)
TELEGRAM_URL_PATTERN = re.compile(r"https?://(?:t\.me|telegram\.me)/([A-Z0-9_]{3,32})", re.IGNORECASE)
AT_HANDLE_PATTERN = re.compile(r"(?<![\w.])@([A-Z][A-Z0-9_]{3,31})\b", re.IGNORECASE)
WECHAT_PATTERN = re.compile(
    r"(?:微信|wechat|weixin|wx)\s*(?:id|账号|帳號)?\s*[:：]?\s*([A-Z0-9_-]{4,32})",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(whatsapp|wa|手机|手機|电话|電話|mobile|phone|tel)\s*[:：]?\s*([+＋]?\d[\d\s().-]{6,}\d)",
    re.IGNORECASE,
)
DISCORD_PATTERN = re.compile(
    r"(?:discord)\s*[:：]?\s*([A-Z0-9_.#-]{3,40}|https?://discord\.gg/[^\s,;]+)",
    re.IGNORECASE,
)

CONTACT_CONTEXT_PATTERN = re.compile(
    r"tg|telegram|投递|投遞|联系|聯絡|联系方式|聯絡方式|contact|apply|私信|dm|简历|簡歷|resume|cv|履歴書",
    re.IGNORECASE,
)
WEB3_SOCIAL_HANDLE_SOURCES = {"abetterweb3", "web3career", "web3jobsai", "dejob"}


def extract_bd_contact_candidates(job: Job) -> list[BdContactCandidate]:
    text = _combined_text(job)
    candidates: list[BdContactCandidate] = []
    candidates.extend(_extract_emails(text))
    candidates.extend(_extract_obfuscated_emails(text))
    candidates.extend(_extract_telegram_urls(text))
    candidates.extend(_extract_at_handles(text, source_name=job.source_name or ""))
    candidates.extend(_extract_wechat(text))
    candidates.extend(_extract_phone_contacts(text))
    candidates.extend(_extract_discord(text))
    company_url = _company_url(job)
    if company_url:
        candidates.append(
            BdContactCandidate(
                contact_type="company_url",
                contact_value=company_url,
                confidence="medium",
                evidence_snippet="company_url from source payload",
            )
        )
    return _dedupe_candidates(candidates)


def _combined_text(job: Job) -> str:
    return "\n".join(value for value in (job.title or "", job.description or "") if value)


def _extract_emails(text: str) -> list[BdContactCandidate]:
    return [
        BdContactCandidate(
            contact_type="email",
            contact_value=_clean_email(match.group(0)),
            confidence="high",
            evidence_snippet=_snippet(text, match.start(), match.end()),
        )
        for match in EMAIL_PATTERN.finditer(text)
    ]


def _extract_obfuscated_emails(text: str) -> list[BdContactCandidate]:
    contacts = []
    for match in OBFUSCATED_EMAIL_PATTERN.finditer(text):
        value = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
        contacts.append(
            BdContactCandidate(
                contact_type="email",
                contact_value=_clean_email(value),
                confidence="medium",
                evidence_snippet=_snippet(text, match.start(), match.end()),
            )
        )
    return contacts


def _extract_telegram_urls(text: str) -> list[BdContactCandidate]:
    return [
        BdContactCandidate(
            contact_type="telegram",
            contact_value=f"@{match.group(1).lower()}",
            confidence="high",
            evidence_snippet=_snippet(text, match.start(), match.end()),
        )
        for match in TELEGRAM_URL_PATTERN.finditer(text)
    ]


def _extract_at_handles(text: str, *, source_name: str) -> list[BdContactCandidate]:
    contacts = []
    for match in AT_HANDLE_PATTERN.finditer(text):
        handle = f"@{match.group(1).lower()}"
        context = _snippet(text, match.start(), match.end(), radius=48)
        if CONTACT_CONTEXT_PATTERN.search(context):
            contact_type = "telegram"
            confidence = "high" if re.search(r"tg|telegram", context, re.IGNORECASE) else "medium"
        elif source_name in WEB3_SOCIAL_HANDLE_SOURCES:
            contact_type = "social_handle"
            confidence = "medium"
        else:
            continue
        contacts.append(
            BdContactCandidate(
                contact_type=contact_type,
                contact_value=handle,
                confidence=confidence,
                evidence_snippet=context,
            )
        )
    return contacts


def _extract_wechat(text: str) -> list[BdContactCandidate]:
    contacts = []
    for match in WECHAT_PATTERN.finditer(text):
        value = match.group(1).strip().strip(".,;:，。；：")
        if not value:
            continue
        contacts.append(
            BdContactCandidate(
                contact_type="wechat",
                contact_value=value,
                confidence="high",
                evidence_snippet=_snippet(text, match.start(), match.end()),
            )
        )
    return contacts


def _extract_phone_contacts(text: str) -> list[BdContactCandidate]:
    contacts = []
    for match in PHONE_PATTERN.finditer(text):
        label = match.group(1).lower()
        value = _normalize_phone(match.group(2))
        if len(value.replace("+", "")) < 7:
            continue
        contacts.append(
            BdContactCandidate(
                contact_type="whatsapp" if label in {"whatsapp", "wa"} else "phone",
                contact_value=value,
                confidence="high",
                evidence_snippet=_snippet(text, match.start(), match.end()),
            )
        )
    return contacts


def _extract_discord(text: str) -> list[BdContactCandidate]:
    return [
        BdContactCandidate(
            contact_type="discord",
            contact_value=match.group(1).strip().strip(".,;:，。；："),
            confidence="medium",
            evidence_snippet=_snippet(text, match.start(), match.end()),
        )
        for match in DISCORD_PATTERN.finditer(text)
    ]


def _company_url(job: Job) -> str | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    company_url = signal_tags.get("company_url")
    if not isinstance(company_url, str):
        return None
    normalized = company_url.strip()
    if not normalized.lower().startswith(("http://", "https://")):
        return None
    return normalized


def _dedupe_candidates(candidates: list[BdContactCandidate]) -> list[BdContactCandidate]:
    by_key: dict[tuple[str, str], BdContactCandidate] = {}
    for candidate in candidates:
        key = (candidate.contact_type, candidate.contact_value)
        existing = by_key.get(key)
        if existing is None or _confidence_rank(candidate.confidence) > _confidence_rank(existing.confidence):
            by_key[key] = candidate
    return list(by_key.values())


def _confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(value, 0)


def _clean_email(value: str) -> str:
    return value.strip().strip(".,;:，。；：)-").lower()


def _normalize_phone(value: str) -> str:
    cleaned = value.strip().replace("＋", "+")
    prefix = "+" if cleaned.startswith("+") else ""
    digits = re.sub(r"\D", "", cleaned)
    return f"{prefix}{digits}"


def _snippet(text: str, start: int, end: int, *, radius: int = 80) -> str:
    compact = " ".join((text or "").split())
    if not compact:
        return ""
    raw_match = text[start:end]
    compact_pos = compact.lower().find(" ".join(raw_match.lower().split()))
    if compact_pos < 0:
        compact_pos = min(start, len(compact))
    snippet_start = max(0, compact_pos - radius)
    snippet_end = min(len(compact), compact_pos + max(len(raw_match), 1) + radius)
    return compact[snippet_start:snippet_end].strip()
