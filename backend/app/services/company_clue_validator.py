import json
import re

from app.services.intelligence import IntelligenceGenerationError


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s，。；,;）)\]]+")

SECTION_KEYS = ("clue_1", "clue_2", "clue_3")
SECTION_TITLES = {
    "clue_1": "线索一：露出的口子",
    "clue_2": "线索二：卡住的岗位",
    "clue_3": "线索三：下手路径",
}
SECTION_KEY_ALIASES = {
    "clue_1": "clue_1",
    "clue_2": "clue_2",
    "clue_3": "clue_3",
    "lead": "clue_1",
    "evidence": "clue_2",
    "next_move": "clue_3",
    "线索一：露出的口子": "clue_1",
    "线索二：卡住的岗位": "clue_2",
    "线索三：下手路径": "clue_3",
    "为什么现在值得查": "clue_1",
    "最能代表需求的岗位": "clue_2",
    "你下一步先验证什么": "clue_3",
}

GENERIC_PHRASES = (
    "表现突出",
    "值得优先关注",
    "整体热度高",
    "建议持续观察",
    "建议重点关注",
)


def parse_company_clue_response(content: str) -> dict:
    try:
        payload = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise IntelligenceGenerationError("Company clue response is not valid JSON") from exc

    sections = _normalize_sections(payload.get("sections"))
    if len(sections) != 3:
        raise IntelligenceGenerationError("Company clue response must contain three sections")

    narrative = payload.get("narrative")
    if isinstance(narrative, str) and narrative.strip():
        narrative_text = narrative.strip()
    else:
        first_content = sections[0].get("content") if isinstance(sections[0], dict) else None
        if not isinstance(first_content, str) or not first_content.strip():
            raise IntelligenceGenerationError("Company clue response is missing narrative")
        narrative_text = first_content.strip()

    normalized = []
    for expected_key, section in zip(SECTION_KEYS, sections):
        if not isinstance(section, dict):
            raise IntelligenceGenerationError("Company clue section keys are invalid")
        section_key = SECTION_KEY_ALIASES.get(section.get("key"))
        if section_key != expected_key:
            raise IntelligenceGenerationError("Company clue section keys are invalid")
        title = section.get("title")
        section_content = section.get("content")
        if not isinstance(title, str) or not title.strip():
            raise IntelligenceGenerationError("Company clue section is missing title")
        if not isinstance(section_content, str) or not section_content.strip():
            raise IntelligenceGenerationError("Company clue section is missing content")
        normalized.append(
            {
                "key": expected_key,
                "title": title.strip(),
                "content": section_content.strip(),
            }
        )
    return {"narrative": narrative_text, "sections": normalized}


def _normalize_sections(sections) -> list:
    if isinstance(sections, list):
        return [_normalize_section_list_item(section) for section in sections]
    if not isinstance(sections, dict):
        raise IntelligenceGenerationError("Company clue response must contain three sections")

    normalized = []
    normalized_by_key: dict[str, object] = {}
    for raw_key, value in sections.items():
        normalized_key = SECTION_KEY_ALIASES.get(raw_key)
        if normalized_key is not None:
            normalized_by_key[normalized_key] = value

    for key in SECTION_KEYS:
        value = normalized_by_key.get(key)
        if isinstance(value, str):
            normalized.append({"key": key, "title": SECTION_TITLES[key], "content": value})
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            normalized.append({"key": key, "title": SECTION_TITLES[key], "content": "\n".join(value)})
        elif isinstance(value, dict):
            normalized.append(
                {
                    "key": key,
                    "title": value.get("title", SECTION_TITLES[key]),
                    "content": value.get("content"),
                }
            )
    return normalized


def _normalize_section_list_item(section) -> object:
    if not isinstance(section, dict) or "key" in section:
        return section
    title = section.get("title")
    title_key = SECTION_KEY_ALIASES.get(title)
    if title_key is not None:
        return {
            "key": title_key,
            "title": title.strip(),
            "content": section.get("content"),
        }
    for raw_key, raw_title in section.items():
        key = SECTION_KEY_ALIASES.get(raw_key)
        if key is not None and isinstance(raw_title, str) and "content" in section:
            return {
                "key": key,
                "title": raw_title.strip() or SECTION_TITLES[key],
                "content": section.get("content"),
            }
    if len(section) != 1:
        return section

    raw_key, value = next(iter(section.items()))
    key = SECTION_KEY_ALIASES.get(raw_key)
    if key is None:
        return section
    if isinstance(value, str):
        return {"key": key, "title": SECTION_TITLES[key], "content": _strip_section_title(value, key)}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        content = "\n".join(_strip_section_title(item, key) for item in value)
        return {"key": key, "title": SECTION_TITLES[key], "content": content}
    if isinstance(value, dict):
        return {
            "key": key,
            "title": value.get("title", SECTION_TITLES[key]),
            "content": value.get("content"),
        }
    return section


def _strip_section_title(content: str, key: str) -> str:
    title = SECTION_TITLES[key]
    stripped = content.strip()
    if stripped.startswith(title):
        return stripped[len(title) :].lstrip(" \t\r\n:：-")
    return stripped


def validate_company_clue_response(payload: dict, *, context: dict) -> None:
    text = " ".join([payload["narrative"], *[section["content"] for section in payload["sections"]]])
    for phrase in GENERIC_PHRASES:
        if phrase in text:
            raise IntelligenceGenerationError(f"Company clue response is generic: {phrase}")

    titles = [card["title"] for card in context.get("evidence_cards", [])]
    if len(titles) >= 2 and sum(1 for title in titles if title in text) < 2:
        raise IntelligenceGenerationError("Company clue response is missing grounded job titles")

    next_move = next(section["content"] for section in payload["sections"] if section["key"] == "clue_3")
    allowed_entry_points = [
        *context.get("entry_points", {}).get("job_posts", []),
        *context.get("entry_points", {}).get("company_urls", []),
        *context.get("entry_points", {}).get("hiring_pages", []),
        *context.get("entry_points", {}).get("emails", []),
    ]
    allowed_entry_points = [item for item in allowed_entry_points if item]
    if allowed_entry_points and not any(item in next_move for item in allowed_entry_points):
        raise IntelligenceGenerationError("Company clue response is missing grounded next-step entry points")

    mentioned_entry_points = [*URL_PATTERN.findall(next_move), *EMAIL_PATTERN.findall(next_move)]
    unapproved_entry_points = [item for item in mentioned_entry_points if item not in allowed_entry_points]
    if unapproved_entry_points:
        raise IntelligenceGenerationError("Company clue response contains unapproved next-step entry points")


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
