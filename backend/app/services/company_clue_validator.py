import json
import re

from app.services.intelligence import IntelligenceGenerationError


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s，。；,;）)]+")

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

    narrative = payload.get("narrative")
    sections = payload.get("sections")
    if not isinstance(narrative, str) or not narrative.strip():
        raise IntelligenceGenerationError("Company clue response is missing narrative")
    if not isinstance(sections, list) or len(sections) != 3:
        raise IntelligenceGenerationError("Company clue response must contain three sections")

    normalized = []
    for expected_key, section in zip(("lead", "evidence", "next_move"), sections):
        if not isinstance(section, dict) or section.get("key") != expected_key:
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
    return {"narrative": narrative.strip(), "sections": normalized}


def validate_company_clue_response(payload: dict, *, context: dict) -> None:
    text = " ".join([payload["narrative"], *[section["content"] for section in payload["sections"]]])
    for phrase in GENERIC_PHRASES:
        if phrase in text:
            raise IntelligenceGenerationError(f"Company clue response is generic: {phrase}")

    titles = [card["title"] for card in context.get("evidence_cards", [])]
    if len(titles) >= 2 and sum(1 for title in titles if title in text) < 2:
        raise IntelligenceGenerationError("Company clue response is missing grounded job titles")

    next_move = next(section["content"] for section in payload["sections"] if section["key"] == "next_move")
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
