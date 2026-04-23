# Company Clue Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework single-company clue generation into a grounded, evidence-driven BD brief that gives more specific next-step guidance while keeping the existing `/api/v1/company-clue` response contract unchanged.

**Architecture:** Keep `company_clue_letter` as a thin orchestrator. Move source-job selection and evidence packing into a dedicated context builder, move prompt/rewrite text into a prompt builder, and move parse/groundedness checks into a validator so the LLM is fed richer evidence without pushing business logic into the API layer or frontend.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy ORM, pytest, existing `Job.signal_tags`, existing Zhipu structured JSON request helper

---

## File Structure

### Create

- `backend/app/services/company_clue_context.py`
  - Owns company job loading within the same 14-day window as the home feed.
  - Builds the grounded `llm_input` evidence pack from existing `Job` rows.
- `backend/app/services/company_clue_prompt.py`
  - Owns system/user/rewrite prompts for the BD brief.
- `backend/app/services/company_clue_validator.py`
  - Owns response parsing plus groundedness, anti-generic, and actionability checks.
- `backend/tests/test_company_clue_context.py`
  - Locks down window alignment and evidence-pack construction.
- `backend/tests/test_company_clue_validator.py`
  - Locks down anti-generic validation and rewrite-trigger conditions.

### Modify

- `backend/app/services/company_clue_letter.py`
  - Keeps orchestration only: load jobs, build context, call LLM, validate, rewrite once if needed, return the existing API contract.
- `backend/tests/test_company_clue_letter.py`
  - Verifies orchestration, 14-day source selection, rewrite behavior, and unchanged response contract.

### Do Not Modify

- `backend/app/api/company_clue.py`
  - Keep API handlers thin and unchanged.
- `backend/app/schemas/company_clue.py`
  - Keep the public response contract unchanged for this phase.
- `frontend/components/CompanyCluePanel.tsx`
  - Existing frontend should consume richer content through the same API shape.
- `frontend/components/CompanyCard.tsx`
  - No frontend behavior change in this phase.
- `backend/app/services/intelligence.py`
  - Reuse `request_zhipu_structured_json`; do not fold company clue rules into the home-intelligence service.

## Target Behavior

The improved company clue should still return:

```json
{
  "status": "success",
  "company": "Aijobs",
  "generated_at": "2026-04-23T12:40:00",
  "narrative": "...",
  "sections": [
    {"key": "lead", "title": "为什么现在值得查", "content": "..."},
    {"key": "evidence", "title": "最能代表需求的岗位", "content": "..."},
    {"key": "next_move", "title": "你下一步先验证什么", "content": "..."}
  ],
  "error_message": null
}
```

The internal generation path should stop feeding only compressed counters. The LLM input must include:

- a 14-day company window aligned with the home feed
- role clusters that explain where hiring is concentrated
- 3-5 evidence cards with job title, timing, signal hits, brief JD snippets, and entry points
- grouped entry points
- estimated bounty when a complete estimate exists

The generated copy must:

- name at least 2 exact job titles when the context has 2 or more evidence cards
- bind next steps to real entry points already present in the data
- distinguish evidence from inference
- avoid generic phrases like “表现突出”“值得优先关注”“整体热度高”“建议持续观察”

---

### Task 1: Build a Grounded Company Clue Context

**Files:**
- Create: `backend/app/services/company_clue_context.py`
- Test: `backend/tests/test_company_clue_context.py`

- [ ] **Step 1: Write the failing test for 14-day alignment and evidence-card shape**

```python
from datetime import datetime, timedelta

from app.models import Job
from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue


def build_job(*, company: str, title: str, days_ago: int, description: str, signal_tags: dict | None = None) -> Job:
    current = datetime(2026, 4, 23, 12, 0, 0) - timedelta(days=days_ago)
    return Job(
        canonical_url=f"https://jobs.example.com/{company.lower()}/{title.lower().replace(' ', '-')}",
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=current,
        collected_at=current,
        bounty_grade="high",
        signal_tags=signal_tags or {"display_tags": ["AI"], "company_url": f"https://{company.lower()}.example.com"},
    )


def test_load_company_jobs_for_clue_uses_same_14_day_window_as_home_feed(db_session):
    db_session.add(build_job(company="OpenGradient", title="Recent Role", days_ago=2, description="urgent ai platform hiring now"))
    db_session.add(build_job(company="OpenGradient", title="Old Role", days_ago=20, description="old archived role"))
    db_session.commit()

    jobs = load_company_jobs_for_clue(db_session, company="OpenGradient", today=datetime(2026, 4, 23, 12, 0, 0).date())

    assert [job.title for job in jobs] == ["Recent Role"]


def test_build_company_clue_context_exposes_grounded_evidence_cards():
    jobs = [
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            days_ago=1,
            description="Urgent AI platform hiring. Build model infra for customer delivery. careers@opengradient.ai",
            signal_tags={
                "display_tags": ["AI", "Senior", "核心岗位"],
                "company_url": "https://opengradient.ai",
                "apply_url": "https://opengradient.ai/careers",
                "estimated_bounty_amount": 150000,
                "estimated_bounty_label": "¥120,000-¥180,000",
                "estimated_bounty_min": 120000,
                "estimated_bounty_max": 180000,
                "estimated_bounty_rate_pct": 20,
                "estimated_bounty_rule_version": "bounty-rule-v1",
                "estimated_bounty_confidence": "medium",
            },
        )
    ]

    context = build_company_clue_context(company="OpenGradient", jobs=jobs, today=datetime(2026, 4, 23, 12, 0, 0).date())

    assert context["window"]["window_days"] == 14
    assert context["summary"]["total_jobs"] == 1
    assert context["summary"]["estimated_bounty"]["amount"] == 150000
    assert context["evidence_cards"][0]["title"] == "Principal AI Engineer"
    assert context["evidence_cards"][0]["entry_points"]["hiring_page"] == "https://opengradient.ai/careers"
    assert context["evidence_cards"][0]["evidence_snippets"]
    assert context["entry_points"]["job_posts"] == [jobs[0].canonical_url]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest backend/tests/test_company_clue_context.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.services.company_clue_context`

- [ ] **Step 3: Write the minimal context builder**

```python
from collections import Counter
from datetime import date, timedelta
import re

from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import BountyEstimate
from app.services.feed_snapshot import WINDOW_DAYS
from app.services.job_facts import StandardizedJobInput, build_v2_score_input, extract_job_facts
from app.services.scoring import score_job_v2


def load_company_jobs_for_clue(db: Session, *, company: str, today: date) -> list[Job]:
    window_start = today - timedelta(days=WINDOW_DAYS - 1)
    jobs = (
        db.query(Job)
        .filter(Job.company == company)
        .order_by(Job.collected_at.desc(), Job.id.desc())
        .all()
    )
    return [job for job in jobs if (job.posted_at or job.collected_at).date() >= window_start]


def build_company_clue_context(*, company: str, jobs: list[Job], today: date) -> dict:
    evidence_cards = [_build_evidence_card(job) for job in jobs]
    categories = Counter(card["category"] for card in evidence_cards)
    domains = Counter(card["domain_tag"] for card in evidence_cards)
    role_clusters = _build_role_clusters(evidence_cards)
    return {
        "company": company,
        "window": {
            "window_days": WINDOW_DAYS,
            "window_start": (today - timedelta(days=WINDOW_DAYS - 1)).isoformat(),
            "window_end": today.isoformat(),
        },
        "summary": {
            "total_jobs": len(jobs),
            "high_bounty_jobs": sum(1 for card in evidence_cards if card["bounty_grade"] == "high"),
            "urgent_jobs": sum(1 for card in evidence_cards if card["urgent"]),
            "critical_jobs": sum(1 for card in evidence_cards if card["critical"]),
            "top_categories": [name for name, _count in categories.most_common(3)],
            "top_domains": [name for name, _count in domains.most_common(3)],
            "estimated_bounty": _collect_estimated_bounty(jobs),
        },
        "role_clusters": role_clusters[:3],
        "evidence_cards": evidence_cards[:5],
        "entry_points": _collect_entry_points(jobs),
    }


def _build_evidence_card(job: Job) -> dict:
    facts = extract_job_facts(
        StandardizedJobInput(
            canonical_url=job.canonical_url,
            source_name=job.source_name,
            title=job.title,
            company=job.company,
            company_normalized=job.company_normalized,
            description=job.description,
            posted_at=job.posted_at,
            collected_at=job.collected_at,
        ),
        now=job.collected_at,
    )
    score_result = score_job_v2(build_v2_score_input(facts))
    return {
        "title": job.title,
        "posted_at": (job.posted_at or job.collected_at).replace(microsecond=0).isoformat(),
        "bounty_grade": job.bounty_grade,
        "category": facts.category,
        "domain_tag": facts.domain_tag,
        "seniority": facts.seniority,
        "urgent": facts.urgent,
        "critical": facts.critical,
        "hard_to_fill": facts.hard_to_fill,
        "business_criticality": facts.business_criticality,
        "time_pressure_signals": list(facts.time_pressure_signals),
        "anomaly_signals": list(facts.anomaly_signals),
        "v2_reasons": list(score_result.reasons),
        "rule_hits": [hit.code for hit in score_result.rule_hits],
        "entry_points": {
            "job_post": job.canonical_url,
            "company_url": _read_signal_tag(job, "company_url"),
            "hiring_page": _read_signal_tag(job, "hiring_page_url", "apply_url"),
            "email": _extract_email(job),
        },
        "evidence_snippets": _extract_evidence_snippets(job.description or ""),
    }


def _build_role_clusters(evidence_cards: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for card in evidence_cards:
        key = (card["category"], card["seniority"])
        cluster = grouped.setdefault(
            key,
            {
                "category": card["category"],
                "seniority": card["seniority"],
                "job_count": 0,
                "titles": [],
                "critical_jobs": 0,
                "urgent_jobs": 0,
            },
        )
        cluster["job_count"] += 1
        cluster["critical_jobs"] += 1 if card["critical"] else 0
        cluster["urgent_jobs"] += 1 if card["urgent"] else 0
        if card["title"] not in cluster["titles"]:
            cluster["titles"].append(card["title"])
    return sorted(grouped.values(), key=lambda item: (-item["job_count"], -item["critical_jobs"], item["category"]))


def _extract_evidence_snippets(description: str) -> list[str]:
    normalized = " ".join(description.split())
    candidates = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\\s+|\\n+", normalized) if chunk.strip()]
    prioritized = [
        chunk
        for chunk in candidates
        if any(token in chunk.lower() for token in ("urgent", "hiring", "architect", "lead", "principal", "manager", "platform", "remote"))
    ]
    selected = prioritized[:2] or candidates[:1]
    return [item[:180] for item in selected]


def _collect_estimated_bounty(jobs: list[Job]) -> dict | None:
    for job in jobs:
        estimate = BountyEstimate.from_signal_tags(job.signal_tags if isinstance(job.signal_tags, dict) else None)
        if estimate is not None:
            return {"amount": estimate.amount, "label": estimate.label}
    return None


def _collect_entry_points(jobs: list[Job]) -> dict:
    company_urls = _dedupe_non_empty(_read_signal_tag(job, "company_url") for job in jobs)
    hiring_pages = _dedupe_non_empty(_read_signal_tag(job, "hiring_page_url", "apply_url") for job in jobs)
    job_posts = _dedupe_non_empty(job.canonical_url for job in jobs)
    emails = _dedupe_non_empty(_extract_email(job) for job in jobs)
    return {
        "company_urls": company_urls[:3],
        "hiring_pages": hiring_pages[:3],
        "job_posts": job_posts[:5],
        "emails": emails[:3],
    }


def _read_signal_tag(job: Job, *keys: str) -> str | None:
    signal_tags = job.signal_tags if isinstance(job.signal_tags, dict) else {}
    for key in keys:
        value = signal_tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_email(job: Job) -> str | None:
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", job.description or "", re.IGNORECASE)
    if match is None:
        return None
    return match.group(0)


def _dedupe_non_empty(values) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if not value or value in deduped:
            continue
        deduped.append(value)
    return deduped
```

- [ ] **Step 4: Run the focused context test**

Run: `pytest backend/tests/test_company_clue_context.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/company_clue_context.py backend/tests/test_company_clue_context.py
git commit -m "feat: add grounded company clue context builder"
```

### Task 2: Add Prompt Builder and Groundedness Validator

**Files:**
- Create: `backend/app/services/company_clue_prompt.py`
- Create: `backend/app/services/company_clue_validator.py`
- Test: `backend/tests/test_company_clue_validator.py`

- [ ] **Step 1: Write the failing validator test**

```python
import pytest

from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import IntelligenceGenerationError


def build_context() -> dict:
    return {
        "company": "OpenGradient",
        "summary": {"total_jobs": 2},
        "evidence_cards": [
            {
                "title": "Principal AI Engineer",
                "entry_points": {"job_post": "https://jobs.example.com/1", "company_url": None, "hiring_page": None, "email": None},
            },
            {
                "title": "Growth Engineer",
                "entry_points": {"job_post": "https://jobs.example.com/2", "company_url": None, "hiring_page": None, "email": None},
            },
        ],
        "entry_points": {"job_posts": ["https://jobs.example.com/1", "https://jobs.example.com/2"], "company_urls": [], "hiring_pages": [], "emails": []},
    }


def test_validate_company_clue_response_rejects_generic_copy():
    payload = parse_company_clue_response(
        '{"narrative":"OpenGradient 表现突出，整体热度高，值得优先关注。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"这家公司值得优先关注。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"岗位比较关键。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"建议持续观察。"}'
        ']}'
    )

    with pytest.raises(IntelligenceGenerationError, match="generic"):
        validate_company_clue_response(payload, context=build_context())


def test_validate_company_clue_response_requires_title_and_entry_point_grounding():
    payload = parse_company_clue_response(
        '{"narrative":"你现在该先查 OpenGradient，因为 Principal AI Engineer 和 Growth Engineer 两个岗位同时出现，说明它在补关键推进位。",'
        '"sections":['
        '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 和 Growth Engineer 同时挂出，说明不是普通补人。"},'
        '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 代表核心技术推进，Growth Engineer 代表业务扩张。"},'
        '{"key":"next_move","title":"你下一步先验证什么","content":"先回到 https://jobs.example.com/1 核对团队职责，再看 https://jobs.example.com/2 是否仍在持续开放。"}'
        ']}'
    )

    validate_company_clue_response(payload, context=build_context())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest backend/tests/test_company_clue_validator.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.services.company_clue_validator`

- [ ] **Step 3: Write the prompt builder**

```python
import json


def build_company_clue_messages(context: dict) -> list[dict]:
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {"role": "user", "content": build_company_clue_user_prompt(context)},
    ]


def build_company_clue_rewrite_messages(*, context: dict, invalid_content: str, validation_error: str) -> list[dict]:
    return [
        {"role": "system", "content": build_company_clue_system_prompt()},
        {
            "role": "user",
            "content": (
                "你上一版输出不合格，请只修正为合格 JSON。"
                f"不合格原因：{validation_error}。"
                "必须保留现有响应 schema：narrative + sections。"
                "必须点名至少 2 个岗位标题，必须把 next_move 绑定到真实入口，禁止泛泛建议。"
                f"\\n\\n结构化输入：\\n{json.dumps(context, ensure_ascii=False)}"
                f"\\n\\n上一版输出：\\n{invalid_content}"
            ),
        },
    ]


def build_company_clue_system_prompt() -> str:
    return (
        "你是猎头酒馆里的 BD 侦查员，正在写单公司 BD 作战简报。"
        "只能依据用户给你的结构化输入判断，不能编造外部信息。"
        "直接输出 JSON 对象，不要 markdown。"
        "JSON 必须包含 narrative 和 sections。"
        "sections 必须固定为 lead、evidence、next_move 三段。"
        "lead 要回答为什么现在值得查；evidence 要点名最能代表需求的岗位；next_move 要给出 3 个可执行验证动作。"
        "必须优先引用 evidence_cards 里的岗位标题、信号、片段和入口。"
        "禁止使用“表现突出”“值得优先关注”“整体热度高”“建议持续观察”这类泛化表述。"
    )


def build_company_clue_user_prompt(context: dict) -> str:
    return (
        "请基于下面的公司证据包生成单公司 BD 作战简报。"
        "必须区分已知事实和推断，不要把推断写成事实。"
        "如果 context 里有两个以上 evidence_cards，全文必须至少点名两个岗位标题。"
        "next_move 必须绑定真实入口链接或邮箱；如果没有公司官网或邮箱，就只允许引用 job_posts。"
        "sections 的标题固定写成“为什么现在值得查”“最能代表需求的岗位”“你下一步先验证什么”。"
        f"\\n\\n结构化输入：\\n{json.dumps(context, ensure_ascii=False)}"
    )
```

- [ ] **Step 4: Write the parser and validator**

```python
import json

from app.services.intelligence import IntelligenceGenerationError


GENERIC_PHRASES = (
    "表现突出",
    "值得优先关注",
    "整体热度高",
    "建议持续观察",
    "建议重点关注",
)


def parse_company_clue_response(content: str) -> dict:
    payload = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
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
        normalized.append(
            {
                "key": expected_key,
                "title": str(section.get("title", "")).strip(),
                "content": str(section.get("content", "")).strip(),
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
    if allowed_entry_points and not any(item in next_move for item in allowed_entry_points):
        raise IntelligenceGenerationError("Company clue response is missing grounded next-step entry points")
```

- [ ] **Step 5: Run the focused validator test**

Run: `pytest backend/tests/test_company_clue_validator.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/company_clue_prompt.py backend/app/services/company_clue_validator.py backend/tests/test_company_clue_validator.py
git commit -m "feat: add company clue prompt and validation layers"
```

### Task 3: Rewire the Company Clue Orchestrator Without Changing the API Contract

**Files:**
- Modify: `backend/app/services/company_clue_letter.py`
- Modify: `backend/tests/test_company_clue_letter.py`

- [ ] **Step 1: Write the failing orchestration test for rewrite and 14-day alignment**

```python
from datetime import datetime, timedelta

from app.models import Job
from app.services.company_clue_letter import generate_company_clue_letter


def build_job(*, company: str, title: str, days_ago: int) -> Job:
    current = datetime(2026, 4, 23, 12, 0, 0) - timedelta(days=days_ago)
    return Job(
        canonical_url=f"https://jobs.example.com/{company.lower()}/{title.lower().replace(' ', '-')}",
        source_name="test",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=f"{title} urgent hiring now",
        posted_at=current,
        collected_at=current,
        bounty_grade="high",
        signal_tags={"display_tags": ["AI"], "company_url": f"https://{company.lower()}.example.com"},
    )


def test_generate_company_clue_letter_rewrites_generic_first_pass_and_uses_windowed_jobs(db_session, monkeypatch):
    db_session.add(build_job(company="OpenGradient", title="Principal AI Engineer", days_ago=1))
    db_session.add(build_job(company="OpenGradient", title="Old Role", days_ago=30))
    db_session.commit()

    calls = []
    monkeypatch.setattr("app.services.company_clue_letter._should_use_company_clue_llm", lambda: True)

    def fake_request(messages):
        calls.append(messages)
        if len(calls) == 1:
            return (
                '{"narrative":"OpenGradient 表现突出，值得优先关注。",'
                '"sections":['
                '{"key":"lead","title":"为什么现在值得查","content":"值得优先关注。"},'
                '{"key":"evidence","title":"最能代表需求的岗位","content":"岗位比较关键。"},'
                '{"key":"next_move","title":"你下一步先验证什么","content":"建议持续观察。"}'
                ']}'
            )
        return (
            '{"narrative":"你现在先查 OpenGradient，因为 Principal AI Engineer 还在 14 天窗口里持续开放，说明它仍在补关键技术推进位。",'
            '"sections":['
            '{"key":"lead","title":"为什么现在值得查","content":"Principal AI Engineer 仍在当前窗口里开放，说明需求还在持续。"},'
            '{"key":"evidence","title":"最能代表需求的岗位","content":"Principal AI Engineer 这类岗位直接对应核心技术推进，不是普通补位。"},'
            '{"key":"next_move","title":"你下一步先验证什么","content":"先回到 https://jobs.example.com/opengradient/principal-ai-engineer 核对职责，再看 https://opengradient.example.com 是否还有相邻岗位。"}'
            ']}'
        )

    monkeypatch.setattr("app.services.company_clue_letter.request_zhipu_structured_json", fake_request)

    result = generate_company_clue_letter(db_session, company="OpenGradient")

    assert result["status"] == "success"
    assert len(calls) == 2
    assert "Principal AI Engineer" in result["narrative"]
    assert "Old Role" not in str(calls[-1])
```

- [ ] **Step 2: Run the orchestration test to verify it fails**

Run: `pytest backend/tests/test_company_clue_letter.py::test_generate_company_clue_letter_rewrites_generic_first_pass_and_uses_windowed_jobs -q`
Expected: FAIL because the current service neither rewrites generic output nor filters to the 14-day window

- [ ] **Step 3: Refactor the orchestrator to use the new services**

```python
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.company_clue_context import build_company_clue_context, load_company_jobs_for_clue
from app.services.company_clue_prompt import build_company_clue_messages, build_company_clue_rewrite_messages
from app.services.company_clue_validator import parse_company_clue_response, validate_company_clue_response
from app.services.intelligence import request_zhipu_structured_json


def generate_company_clue_letter(db: Session, *, company: str) -> dict:
    now = datetime.now().replace(microsecond=0)
    jobs = load_company_jobs_for_clue(db, company=company, today=now.date())
    generated_at = _resolve_generated_at(jobs, fallback=now)

    if not jobs:
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company not found",
            narrative=f"{company} 的单公司线索来信当前无法生成，因为统一 14 天基线里没有这家公司的精确匹配资料。",
        )
    if not _should_use_company_clue_llm():
        return _build_failure_response(
            company=company,
            generated_at=generated_at,
            error_message="Company clue generation unavailable",
            narrative=f"{company} 的单公司线索来信当前不可用，请稍后再试。",
        )

    context = build_company_clue_context(company=company, jobs=jobs, today=now.date())
    payload = _request_and_validate(context)
    return {
        "status": "success",
        "company": company,
        "generated_at": generated_at,
        "narrative": payload["narrative"],
        "sections": payload["sections"],
        "error_message": None,
    }


def _request_and_validate(context: dict) -> dict:
    messages = build_company_clue_messages(context)
    first_response = request_zhipu_structured_json(messages)
    try:
        parsed = parse_company_clue_response(first_response)
        validate_company_clue_response(parsed, context=context)
        return parsed
    except Exception as exc:
        retry_messages = build_company_clue_rewrite_messages(
            context=context,
            invalid_content=first_response,
            validation_error=str(exc),
        )
        repaired_response = request_zhipu_structured_json(retry_messages)
        repaired = parse_company_clue_response(repaired_response)
        validate_company_clue_response(repaired, context=context)
        return repaired


def _resolve_generated_at(jobs: list, *, fallback: datetime) -> str:
    if jobs:
        latest = jobs[0].collected_at.replace(microsecond=0)
        return latest.isoformat()
    return fallback.isoformat()
```

- [ ] **Step 4: Update the existing regression tests**

Add assertions to `backend/tests/test_company_clue_letter.py` so that:

```python
assert set(llm_input.keys()) == {"company", "window", "summary", "role_clusters", "evidence_cards", "entry_points"}
assert "description" not in llm_input["evidence_cards"][0]
assert llm_input["window"]["window_days"] == 14
assert [section["key"] for section in result["sections"]] == ["lead", "evidence", "next_move"]
```

- [ ] **Step 5: Run the focused suite**

Run: `pytest backend/tests/test_company_clue_context.py backend/tests/test_company_clue_validator.py backend/tests/test_company_clue_letter.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/company_clue_letter.py backend/tests/test_company_clue_letter.py
git commit -m "feat: ground company clue generation in evidence packs"
```

### Task 4: Run the Minimal Regression and Local Smoke Check

**Files:**
- Modify: none

- [ ] **Step 1: Run the full minimal regression bundle**

Run: `pytest backend/tests/test_company_clue_context.py backend/tests/test_company_clue_validator.py backend/tests/test_company_clue_letter.py -q`
Expected: PASS

- [ ] **Step 2: Run the company clue API contract test**

Run: `pytest backend/tests/test_company_clue_letter.py::test_company_clue_endpoint_returns_service_contract -q`
Expected: PASS

- [ ] **Step 3: Start the local backend and smoke the endpoint**

Run:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: startup succeeds with no import errors

- [ ] **Step 4: If the local `.env` already contains a valid Zhipu key, smoke a real company request**

Run:

```bash
python - <<'PY'
import requests
payload = requests.post(
    "http://127.0.0.1:8000/api/v1/company-clue",
    json={"company": "Aijobs"},
    timeout=20,
).json()
print(payload["status"])
print(payload["sections"][0]["title"])
print(payload["sections"][0]["content"])
print(payload["sections"][2]["content"])
PY
```

Expected:
- `status` prints `success`
- `lead` section names at least one exact role title
- `next_move` section contains at least one real job-post URL from the payload context

- [ ] **Step 5: Final commit**

```bash
git add backend/app/services/company_clue_context.py backend/app/services/company_clue_prompt.py backend/app/services/company_clue_validator.py backend/app/services/company_clue_letter.py backend/tests/test_company_clue_context.py backend/tests/test_company_clue_validator.py backend/tests/test_company_clue_letter.py
git commit -m "feat: ship grounded company clue briefs"
```

## Self-Review

### Spec Coverage

- richer evidence input: yes, via `company_clue_context.py`
- low-coupling decomposition: yes, via `context` / `prompt` / `validator` / `orchestrator`
- unchanged public API contract: yes, `narrative + sections` stays unchanged
- anti-generic and grounded next steps: yes, via validator + rewrite path
- same 14-day window as home feed: yes, via `WINDOW_DAYS` reuse

### Placeholder Scan

- no `TODO` or `TBD`
- every task includes exact files, concrete tests, and concrete commands
- all code-edit steps include explicit code snippets

### Type Consistency

- public response keys remain `status`, `company`, `generated_at`, `narrative`, `sections`, `error_message`
- section keys remain `lead`, `evidence`, `next_move`
- internal context keys remain `company`, `window`, `summary`, `role_clusters`, `evidence_cards`, `entry_points`

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-company-clue-brief-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
