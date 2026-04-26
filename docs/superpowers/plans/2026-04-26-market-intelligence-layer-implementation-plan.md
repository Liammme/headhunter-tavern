# Market Intelligence Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a permanent market intelligence layer that turns crawled AI/Web3 jobs into compact long-term market reports without feeding full job data or BD/bounty fields to the LLM.

**Architecture:** Keep short-lived raw jobs in `jobs`, add a dedicated `market_intelligence_snapshots` table for permanent compact snapshots, and route the home page through the latest successful market snapshot before falling back to the existing instantaneous intelligence logic. Local development should use a local PostgreSQL database, not the production PostgreSQL database.

**Tech Stack:** FastAPI, SQLAlchemy 2.x ORM, PostgreSQL via `psycopg`, existing pytest stack, existing Next.js/Vitest frontend.

---

## Decisions

- Local development database should be PostgreSQL, using a local database such as `bounty_pool_dev`.
- Local development must not point `DATABASE_URL` at the production database.
- SQLite remains useful for fast unit tests, but PostgreSQL smoke tests are required before release.
- First phase should only add a new table. Do not alter existing production tables until a migration and rollback plan exists.
- New market intelligence services should not reuse the old homepage LLM input builder because that path contains source links, bounty fields, claim state, and BD-oriented semantics.
- First frontend phase keeps the `/api/v1/home` contract stable and only makes long `narrative` text scrollable.

## File Map

- Create `backend/app/models/market_intelligence_snapshot.py`: SQLAlchemy model for permanent market snapshots.
- Modify `backend/app/models/__init__.py`: export `MarketIntelligenceSnapshot`.
- Modify `backend/app/db/init_db.py`: import the new model before `Base.metadata.create_all()`.
- Create `backend/app/services/market_theme_classifier.py`: lightweight rule-based theme classifier.
- Create `backend/app/services/market_signal_builder.py`: compress `Job` rows into sanitized 1d/7d/30d/90d market signals.
- Create `backend/app/services/market_intelligence_report.py`: prompt construction, LLM call, JSON parsing, schema/content validation, fallback report generation.
- Create `backend/app/services/market_intelligence_snapshot_service.py`: orchestrate signal building, report generation, and snapshot persistence.
- Create `backend/app/services/market_intelligence_read_service.py`: read latest successful snapshot and adapt it to existing home `intelligence` shape.
- Modify `backend/app/services/daily_bounty_service.py`: generate market snapshot after crawl completes, without blocking crawl/home summary if intelligence fails.
- Modify `backend/app/services/home_feed.py`: prefer latest successful market snapshot for `intelligence`, then fall back to old `build_intelligence_snapshot()`.
- Modify `backend/app/services/job_upsert_service.py`: change raw job retention from 14 to 30 days after snapshots are stable.
- Modify `frontend/app/globals.css`: add scroll behavior for long intelligence narrative.
- Modify `frontend/components/IntelligencePanel.test.tsx`: cover long narrative rendering/scroll container.
- Add backend tests under `backend/tests/test_market_intelligence_*.py`.
- Modify `deploy/README.md` and `deploy/ops-runbook.md`: document PostgreSQL init/smoke steps for the new snapshot table release.

---

### Task 1: Local PostgreSQL Development Baseline

**Files:**
- Reference: `docs/superpowers/specs/2026-04-26-market-intelligence-layer-design.md`
- Reference: `docs/superpowers/plans/2026-04-26-market-intelligence-layer-implementation-plan.md`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Confirm existing PostgreSQL URL normalization tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_config.py
```

Expected: all config tests pass, including `postgres://` and `postgresql://` normalization to `postgresql+psycopg://`.

- [ ] **Step 2: Create a local PostgreSQL database outside the repo**

Use PowerShell or PostgreSQL tools. Do not write the password into committed files.

```powershell
createdb bounty_pool_dev
```

Expected: local database `bounty_pool_dev` exists. If `createdb` is not on `PATH`, create the same database with pgAdmin or `psql`.

- [ ] **Step 3: Point local `.env` to the local PostgreSQL database**

Edit only `F:\赏金猎人\backend\.env`. Do not commit it and do not paste the value into logs.

Expected shape:

```text
DATABASE_URL=postgresql+psycopg://<local-user>:<local-password>@127.0.0.1:5432/bounty_pool_dev
```

- [ ] **Step 4: Initialize the local PostgreSQL schema**

Run:

```powershell
cd F:\赏金猎人\backend
python -c "from app.db.init_db import init_db; init_db()"
```

Expected: command exits with code 0 and creates current tables in the local PostgreSQL database.

- [ ] **Step 5: Run the backend smoke suite against local PostgreSQL**

Run:

```powershell
cd F:\赏金猎人\backend
python -m app.cli.daily_bounty
pytest -q
```

Expected: `daily_bounty` completes without leaking secrets, and tests pass. If tests still use isolated SQLite through fixtures, also manually verify local PostgreSQL tables exist.

---

### Task 2: Add Permanent Market Snapshot Model

**Files:**
- Create: `backend/app/models/market_intelligence_snapshot.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/init_db.py`
- Test: `backend/tests/test_market_intelligence_snapshot_model.py`

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/test_market_intelligence_snapshot_model.py`:

```python
from datetime import date, datetime

from sqlalchemy import select

from app.models import MarketIntelligenceSnapshot


def test_market_intelligence_snapshot_round_trips_payloads(db_session):
    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=date(2026, 4, 26),
        generated_at=datetime(2026, 4, 26, 14, 0, 0),
        window_days=90,
        market_signal_payload={"windows": {"30d": {"job_count": 12}}},
        report_payload={"headline": "AI infra hiring is rising", "narrative": "30d signal"},
        model_name="deepseek-v4-flash",
        status="success",
        error_message=None,
    )
    db_session.add(snapshot)
    db_session.commit()

    loaded = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()

    assert loaded.snapshot_date == date(2026, 4, 26)
    assert loaded.window_days == 90
    assert loaded.status == "success"
    assert loaded.market_signal_payload["windows"]["30d"]["job_count"] == 12
    assert loaded.report_payload["headline"] == "AI infra hiring is rising"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_snapshot_model.py
```

Expected: import failure for `MarketIntelligenceSnapshot`.

- [ ] **Step 3: Add the model**

Create `backend/app/models/market_intelligence_snapshot.py`:

```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MarketIntelligenceSnapshot(Base):
    __tablename__ = "market_intelligence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    window_days: Mapped[int] = mapped_column(Integer, default=90)
    market_signal_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    report_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Export and initialize the model**

Modify `backend/app/models/__init__.py` to import/export `MarketIntelligenceSnapshot`.

Modify `backend/app/db/init_db.py` to import `market_intelligence_snapshot` and include it in the `_ = (...)` tuple.

- [ ] **Step 5: Run model test**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_snapshot_model.py
```

Expected: test passes.

---

### Task 3: Build Sanitized Market Signals

**Files:**
- Create: `backend/app/services/market_theme_classifier.py`
- Create: `backend/app/services/market_signal_builder.py`
- Test: `backend/tests/test_market_intelligence_signals.py`

- [ ] **Step 1: Write failing signal tests**

Create `backend/tests/test_market_intelligence_signals.py`:

```python
from datetime import date, datetime, timedelta

from app.models import Job
from app.services.market_signal_builder import build_market_signal_payload


def _job(title, company, description, *, days_ago=0, signal_tags=None):
    now = datetime(2026, 4, 26, 10, 0, 0)
    return Job(
        canonical_url=f"https://example.com/{company}/{title}",
        source_name="Aijobs",
        title=title,
        company=company,
        company_normalized=company.lower(),
        description=description,
        posted_at=now - timedelta(days=days_ago),
        collected_at=now - timedelta(days=days_ago),
        job_category="技术",
        domain_tag="AI",
        bounty_grade="high",
        signal_tags=signal_tags or {"claimed_names": ["Alice"], "bd_entry": "email", "salary": "100K-200K"},
    )


def test_market_signal_payload_uses_whitelisted_fields_only():
    payload = build_market_signal_payload(
        jobs=[
            _job(
                "AI Infrastructure Engineer",
                "OpenGradient",
                "Build LLM serving, RAG systems, Kubernetes model deployment, and enterprise AI platform.",
            )
        ],
        snapshot_date=date(2026, 4, 26),
    )

    serialized = str(payload)

    assert "1d" in payload["windows"]
    assert "30d" in payload["windows"]
    assert "90d" in payload["windows"]
    assert payload["representative_samples"][0]["company"] == "OpenGradient"
    assert payload["representative_samples"][0]["domain"] == "AI infra"
    assert "canonical_url" not in serialized
    assert "source_name" not in serialized
    assert "bounty" not in serialized.lower()
    assert "claimed" not in serialized.lower()
    assert "bd_entry" not in serialized
    assert "Build LLM serving, RAG systems, Kubernetes model deployment, and enterprise AI platform." not in serialized
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_signals.py
```

Expected: import failure for `market_signal_builder`.

- [ ] **Step 3: Add theme classifier**

Create `backend/app/services/market_theme_classifier.py`:

```python
THEME_KEYWORDS = {
    "AI infra": ("llm", "model deployment", "kubernetes", "serving", "inference", "platform"),
    "agent / RAG": ("agent", "rag", "retrieval", "workflow", "tool use"),
    "data platform": ("data pipeline", "warehouse", "analytics", "etl"),
    "Web3 infra": ("protocol", "node", "validator", "rpc", "chain"),
    "wallet / payment": ("wallet", "payment", "card", "fiat", "settlement"),
    "security": ("security", "audit", "threat", "vulnerability"),
    "risk / compliance": ("risk", "compliance", "kyc", "aml", "fraud"),
    "trading infra": ("trading", "market making", "exchange", "liquidity"),
    "developer tools": ("sdk", "api", "developer", "tooling"),
    "enterprise AI integration": ("enterprise", "implementation", "deployment", "solution"),
}


def classify_market_theme(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return theme
    return "other"
```

- [ ] **Step 4: Add signal builder**

Create `backend/app/services/market_signal_builder.py` with these public functions:

```python
from datetime import date, datetime, time, timedelta

from app.models import Job
from app.services.market_theme_classifier import classify_market_theme

WINDOWS = (1, 7, 30, 90)
MAX_SAMPLE_SUMMARY_CHARS = 160


def build_market_signal_payload(*, jobs: list[Job], snapshot_date: date) -> dict:
    sample_jobs = _jobs_in_window(jobs, snapshot_date=snapshot_date, window_days=90)
    samples = [_build_representative_sample(job) for job in sample_jobs[:12]]
    return {
        "snapshot_date": snapshot_date.isoformat(),
        "windows": {
            f"{window_days}d": _build_window_summary(jobs, snapshot_date=snapshot_date, window_days=window_days)
            for window_days in WINDOWS
        },
        "representative_samples": samples,
        "historical_comparison": {
            "continuing_signals": [],
            "reversals": [],
            "emerging_signals": [],
        },
    }


def _build_window_summary(jobs: list[Job], *, snapshot_date: date, window_days: int) -> dict:
    window_jobs = _jobs_in_window(jobs, snapshot_date=snapshot_date, window_days=window_days)
    themes: dict[str, int] = {}
    functions: dict[str, int] = {}
    for job in window_jobs:
        theme = classify_market_theme(job.title or "", job.description or "")
        themes[theme] = themes.get(theme, 0) + 1
        functions[job.job_category or "其他"] = functions.get(job.job_category or "其他", 0) + 1
    return {
        "job_count": len(window_jobs),
        "theme_counts": themes,
        "function_counts": functions,
    }


def _jobs_in_window(jobs: list[Job], *, snapshot_date: date, window_days: int) -> list[Job]:
    end = datetime.combine(snapshot_date, time.max)
    start = end - timedelta(days=window_days)
    return [
        job
        for job in jobs
        if (job.collected_at or job.posted_at) is not None and start <= (job.collected_at or job.posted_at) <= end
    ]


def _build_representative_sample(job: Job) -> dict:
    theme = classify_market_theme(job.title or "", job.description or "")
    return {
        "company": job.company,
        "title": job.title,
        "posted_date": (job.posted_at or job.collected_at).date().isoformat() if (job.posted_at or job.collected_at) else None,
        "function": job.job_category,
        "domain": theme,
        "seniority": _infer_seniority(job.title or ""),
        "tech_keywords": _extract_keywords(job.description or "", ("LLM", "RAG", "Kubernetes", "Python", "Solidity")),
        "business_keywords": _extract_keywords(job.description or "", ("enterprise", "payment", "risk", "compliance", "developer")),
        "jd_summary": _summarize_description(job.description or ""),
        "signal_reason": f"{theme} signal appears in a current hiring sample.",
    }


def _infer_seniority(title: str) -> str:
    lowered = title.lower()
    if "principal" in lowered or "staff" in lowered or "lead" in lowered:
        return "Lead"
    if "senior" in lowered or "sr." in lowered:
        return "Senior"
    return "Mid"


def _extract_keywords(text: str, candidates: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [candidate for candidate in candidates if candidate.lower() in lowered]


def _summarize_description(description: str) -> str:
    collapsed = " ".join(description.split())
    return collapsed[:MAX_SAMPLE_SUMMARY_CHARS]
```

- [ ] **Step 5: Run signal tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_signals.py
```

Expected: tests pass and payload contains no source/link/bounty/claim/BD fields.

---

### Task 4: Add LLM Report Schema and Quality Gate

**Files:**
- Create: `backend/app/services/market_intelligence_report.py`
- Test: `backend/tests/test_market_intelligence_report.py`

- [ ] **Step 1: Write failing report validator tests**

Create `backend/tests/test_market_intelligence_report.py`:

```python
import pytest

from app.services.market_intelligence_report import (
    MarketIntelligenceReportError,
    parse_market_intelligence_report,
    validate_market_intelligence_report,
)


def _valid_report():
    return {
        "headline": "AI infra hiring is becoming more execution-oriented",
        "narrative": "30d and 90d signals show AI infra hiring moving from experiments into deployment work.",
        "primary_judgment": {
            "claim": "AI infra demand is shifting toward production deployment.",
            "why_it_matters": "The market is paying for engineering capacity around serving, data, and reliability.",
            "confidence": "medium",
        },
        "perspectives": [
            {"lens": "industry", "judgment": "AI infra remains the strongest signal.", "evidence": ["30d AI infra count rose"]},
            {"lens": "product_business", "judgment": "Companies need deployment capacity.", "evidence": ["Enterprise deployment appears"]},
            {"lens": "organization_hiring", "judgment": "Senior engineering hiring is visible.", "evidence": ["Senior roles appear"]},
        ],
        "trend_cards": [
            {
                "title": "AI infra stays warm",
                "direction": "rising",
                "time_horizon": "30d",
                "judgment": "Infrastructure jobs remain prominent.",
                "evidence": ["AI infra samples"],
                "confidence": "medium",
            }
        ],
        "watchlist": ["Whether enterprise deployment roles keep appearing"],
    }


def test_validate_market_intelligence_report_accepts_valid_payload():
    validate_market_intelligence_report(_valid_report(), allowed_terms={"AI infra", "OpenGradient"})


def test_validate_market_intelligence_report_rejects_bounty_or_bd_language():
    payload = _valid_report()
    payload["narrative"] = "30d trend is strong, BD can use high bounty roles."

    with pytest.raises(MarketIntelligenceReportError, match="banned"):
        validate_market_intelligence_report(payload, allowed_terms={"AI infra"})


def test_validate_market_intelligence_report_requires_all_perspectives():
    payload = _valid_report()
    payload["perspectives"] = payload["perspectives"][:1]

    with pytest.raises(MarketIntelligenceReportError, match="perspectives"):
        validate_market_intelligence_report(payload, allowed_terms={"AI infra"})


def test_parse_market_intelligence_report_accepts_code_fence():
    payload = parse_market_intelligence_report("```json\n{\"headline\":\"x\"}\n```")

    assert payload == {"headline": "x"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_report.py
```

Expected: import failure for `market_intelligence_report`.

- [ ] **Step 3: Add parser and validator**

Create `backend/app/services/market_intelligence_report.py` with:

```python
import json

from app.core.config import settings
from app.services.llm_client import request_structured_json, should_use_llm

BANNED_PHRASES = (
    "BD",
    "猎头",
    "赏金",
    "认领",
    "客户开发",
    "岗位来源",
    "canonical_url",
    "source_name",
    "根据数据分析可得",
    "综合来看",
    "建议持续关注",
)
REQUIRED_LENSES = {"industry", "product_business", "organization_hiring"}
CONFIDENCE_VALUES = {"low", "medium", "high"}
TREND_DIRECTIONS = {"rising", "cooling", "shifting", "stable", "emerging"}
TIME_HORIZONS = {"7d", "30d", "90d"}


class MarketIntelligenceReportError(Exception):
    pass


def build_market_intelligence_system_prompt() -> str:
    return (
        "你是 AI/Web3 招聘市场研究分析师。只能基于用户提供的结构化市场信号判断，不能编造外部事实。"
        "输出必须是合法 JSON，不要 markdown。必须包含 headline、narrative、primary_judgment、perspectives、trend_cards、watchlist。"
        "narrative 是 300-600 字产业研究短报，必须包含 30d 或 90d 视角。"
        "禁止 BD、猎头、赏金、认领、客户开发、岗位来源、岗位链接。"
        "不要报告腔，不要只复述数量，必须给出主线判断、证据和时间视角。"
    )


def build_market_intelligence_user_prompt(signal_payload: dict) -> str:
    return "结构化市场信号：\n" + json.dumps(signal_payload, ensure_ascii=False)


def generate_market_report(signal_payload: dict) -> dict:
    if not should_use_llm():
        return build_rule_market_report(signal_payload)

    content = request_structured_json(
        [
            {"role": "system", "content": build_market_intelligence_system_prompt()},
            {"role": "user", "content": build_market_intelligence_user_prompt(signal_payload)},
        ]
    )
    payload = parse_market_intelligence_report(content)
    validate_market_intelligence_report(payload, allowed_terms=_allowed_terms(signal_payload))
    return payload


def parse_market_intelligence_report(content: str) -> dict:
    normalized = content.strip()
    if normalized.startswith("```json"):
        normalized = normalized.removeprefix("```json").removesuffix("```").strip()
    elif normalized.startswith("```"):
        normalized = normalized.removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise MarketIntelligenceReportError("response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise MarketIntelligenceReportError("response must be a JSON object")
    return payload


def validate_market_intelligence_report(payload: dict, *, allowed_terms: set[str]) -> None:
    for field in ("headline", "narrative", "primary_judgment", "perspectives", "trend_cards", "watchlist"):
        if field not in payload:
            raise MarketIntelligenceReportError(f"missing {field}")

    narrative = _string_field(payload, "narrative")
    if "30d" not in narrative and "90d" not in narrative:
        raise MarketIntelligenceReportError("narrative must include 30d or 90d perspective")
    _reject_banned_text(json.dumps(payload, ensure_ascii=False))

    primary = payload["primary_judgment"]
    if not isinstance(primary, dict) or primary.get("confidence") not in CONFIDENCE_VALUES:
        raise MarketIntelligenceReportError("primary_judgment confidence is invalid")

    perspectives = payload["perspectives"]
    if not isinstance(perspectives, list):
        raise MarketIntelligenceReportError("perspectives must be a list")
    lenses = {item.get("lens") for item in perspectives if isinstance(item, dict)}
    if not REQUIRED_LENSES.issubset(lenses):
        raise MarketIntelligenceReportError("perspectives must cover required lenses")

    trend_cards = payload["trend_cards"]
    if not isinstance(trend_cards, list) or len(trend_cards) > 4:
        raise MarketIntelligenceReportError("trend_cards must contain at most four cards")
    for card in trend_cards:
        if not isinstance(card, dict):
            raise MarketIntelligenceReportError("trend card must be an object")
        if card.get("direction") not in TREND_DIRECTIONS:
            raise MarketIntelligenceReportError("trend direction is invalid")
        if card.get("time_horizon") not in TIME_HORIZONS:
            raise MarketIntelligenceReportError("trend time_horizon is invalid")
        if card.get("confidence") not in CONFIDENCE_VALUES:
            raise MarketIntelligenceReportError("trend confidence is invalid")

    watchlist = payload["watchlist"]
    if not isinstance(watchlist, list) or len(watchlist) > 3:
        raise MarketIntelligenceReportError("watchlist must contain at most three items")


def build_rule_market_report(signal_payload: dict) -> dict:
    return {
        "headline": "市场信号仍在累积",
        "narrative": "30d 和 90d 视角下，当前样本还不足以支持强判断。先把主题、职能和关键词变化作为基线沉淀，后续用连续快照判断哪些方向是真正升温，哪些只是短期岗位波动。",
        "primary_judgment": {
            "claim": "市场信号仍在累积。",
            "why_it_matters": "冷启动阶段应避免把少量新增岗位解读成行业趋势。",
            "confidence": "low",
        },
        "perspectives": [
            {"lens": "industry", "judgment": "主题基线正在建立。", "evidence": []},
            {"lens": "product_business", "judgment": "业务能力变化需要更多快照验证。", "evidence": []},
            {"lens": "organization_hiring", "judgment": "组织招聘变化暂不做强判断。", "evidence": []},
        ],
        "trend_cards": [],
        "watchlist": ["继续观察 30d 与 90d 主题结构是否稳定变化"],
    }


def _reject_banned_text(text: str) -> None:
    for phrase in BANNED_PHRASES:
        if phrase in text:
            raise MarketIntelligenceReportError(f"banned phrase: {phrase}")


def _string_field(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MarketIntelligenceReportError(f"{field} must be a non-empty string")
    return value


def _allowed_terms(signal_payload: dict) -> set[str]:
    terms = set()
    for sample in signal_payload.get("representative_samples", []):
        if isinstance(sample, dict):
            terms.update(str(sample.get(key) or "") for key in ("company", "title", "domain"))
    return {term for term in terms if term}
```

- [ ] **Step 4: Run report tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_report.py
```

Expected: tests pass.

---

### Task 5: Persist Market Intelligence Snapshots

**Files:**
- Create: `backend/app/services/market_intelligence_snapshot_service.py`
- Test: `backend/tests/test_market_intelligence_snapshot_service.py`

- [ ] **Step 1: Write failing snapshot service tests**

Create `backend/tests/test_market_intelligence_snapshot_service.py`:

```python
from datetime import date, datetime

from sqlalchemy import select

from app.models import Job, MarketIntelligenceSnapshot
from app.services.market_intelligence_snapshot_service import generate_daily_market_intelligence_snapshot


def test_generate_daily_market_intelligence_snapshot_writes_success(db_session, monkeypatch):
    db_session.add(
        Job(
            canonical_url="https://example.com/job",
            source_name="Aijobs",
            title="Senior AI Infrastructure Engineer",
            company="OpenGradient",
            company_normalized="opengradient",
            description="Build LLM serving and Kubernetes deployment for enterprise AI.",
            posted_at=datetime(2026, 4, 26, 9, 0, 0),
            collected_at=datetime(2026, 4, 26, 10, 0, 0),
            job_category="技术",
            domain_tag="AI",
            bounty_grade="high",
            signal_tags={},
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.market_intelligence_snapshot_service.generate_market_report",
        lambda signal_payload: {
            "headline": "AI infra keeps rising",
            "narrative": "30d signals show AI infra demand moving into deployment.",
            "primary_judgment": {"claim": "AI infra", "why_it_matters": "deployment", "confidence": "medium"},
            "perspectives": [
                {"lens": "industry", "judgment": "AI infra", "evidence": []},
                {"lens": "product_business", "judgment": "deployment", "evidence": []},
                {"lens": "organization_hiring", "judgment": "senior engineering", "evidence": []},
            ],
            "trend_cards": [],
            "watchlist": [],
        },
    )

    result = generate_daily_market_intelligence_snapshot(db_session, snapshot_date=date(2026, 4, 26))

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result["status"] == "success"
    assert snapshot.status == "success"
    assert snapshot.report_payload["headline"] == "AI infra keeps rising"
    assert "canonical_url" not in str(snapshot.market_signal_payload)


def test_generate_daily_market_intelligence_snapshot_records_failure(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.market_intelligence_snapshot_service.generate_market_report",
        lambda signal_payload: (_ for _ in ()).throw(RuntimeError("llm unavailable")),
    )

    result = generate_daily_market_intelligence_snapshot(db_session, snapshot_date=date(2026, 4, 26))

    snapshot = db_session.execute(select(MarketIntelligenceSnapshot)).scalar_one()
    assert result["status"] == "failed"
    assert snapshot.status == "failed"
    assert "llm unavailable" in snapshot.error_message
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_snapshot_service.py
```

Expected: import failure for `market_intelligence_snapshot_service`.

- [ ] **Step 3: Add snapshot service**

Create `backend/app/services/market_intelligence_snapshot_service.py`:

```python
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, MarketIntelligenceSnapshot
from app.services.market_intelligence_report import generate_market_report
from app.services.market_signal_builder import build_market_signal_payload


def generate_daily_market_intelligence_snapshot(
    db: Session,
    *,
    snapshot_date: date | None = None,
    clock=datetime.now,
) -> dict[str, Any]:
    generated_at = clock().replace(microsecond=0)
    target_date = snapshot_date or generated_at.date()
    jobs = db.execute(select(Job)).scalars().all()
    signal_payload = build_market_signal_payload(jobs=jobs, snapshot_date=target_date)

    try:
        report_payload = generate_market_report(signal_payload)
    except Exception as exc:  # noqa: BLE001
        snapshot = MarketIntelligenceSnapshot(
            snapshot_date=target_date,
            generated_at=generated_at,
            window_days=90,
            market_signal_payload=signal_payload,
            report_payload={},
            model_name=None,
            status="failed",
            error_message=str(exc),
        )
        db.add(snapshot)
        db.commit()
        return {"status": "failed", "error": str(exc)}

    snapshot = MarketIntelligenceSnapshot(
        snapshot_date=target_date,
        generated_at=generated_at,
        window_days=90,
        market_signal_payload=signal_payload,
        report_payload=report_payload,
        model_name=None,
        status="success",
        error_message=None,
    )
    db.add(snapshot)
    db.commit()
    return {"status": "success", "snapshot_id": snapshot.id}
```

- [ ] **Step 4: Run service tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_snapshot_service.py
```

Expected: tests pass.

---

### Task 6: Integrate Snapshot Generation Into daily_bounty

**Files:**
- Modify: `backend/app/services/daily_bounty_service.py`
- Test: `backend/tests/test_daily_bounty_service.py`

- [ ] **Step 1: Add failing daily_bounty test**

Add to `backend/tests/test_daily_bounty_service.py`:

```python
def test_run_daily_bounty_generation_generates_market_snapshot(db_session, monkeypatch):
    calls = []

    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {"fetched_jobs": 1, "new_jobs": 1, "source_stats": {"Aijobs": 1}, "errors": []},
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        lambda db: calls.append("market") or {"status": "success", "snapshot_id": 1},
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 1, "jobs": [{}]}]),
    )

    summary = run_daily_bounty_generation(db_session)

    assert calls == ["market"]
    assert summary["status"] == "completed"


def test_run_daily_bounty_generation_keeps_crawl_success_when_market_snapshot_fails(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.daily_bounty_service.trigger_crawl",
        lambda db: {"fetched_jobs": 1, "new_jobs": 1, "source_stats": {"Aijobs": 1}, "errors": []},
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.generate_daily_market_intelligence_snapshot",
        lambda db: (_ for _ in ()).throw(RuntimeError("market intelligence failed")),
    )
    monkeypatch.setattr(
        "app.services.daily_bounty_service.get_home_payload",
        lambda db: _home_payload([{"company": "OpenGradient", "total_jobs": 1, "jobs": [{}]}]),
    )

    summary = run_daily_bounty_generation(db_session)

    assert summary["status"] == "completed_with_errors"
    assert "market_intelligence: market intelligence failed" in summary["errors"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_daily_bounty_service.py
```

Expected: monkeypatch target for `generate_daily_market_intelligence_snapshot` is missing.

- [ ] **Step 3: Modify daily_bounty service**

In `backend/app/services/daily_bounty_service.py`, import:

```python
from app.services.market_intelligence_snapshot_service import generate_daily_market_intelligence_snapshot
```

After `trigger_crawl(db)` succeeds or fails, and before `get_home_payload(db)`, call the snapshot service in a separate try/except:

```python
    try:
        market_result = generate_daily_market_intelligence_snapshot(db)
        if market_result.get("status") == "failed":
            errors.append(f"market_intelligence: {market_result.get('error')}")
            status = "completed_with_errors" if status == "completed" else status
    except Exception as exc:  # noqa: BLE001
        errors.append(f"market_intelligence: {exc}")
        status = "completed_with_errors" if status == "completed" else status
```

- [ ] **Step 4: Run daily_bounty tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_daily_bounty_service.py
```

Expected: tests pass.

---

### Task 7: Read Latest Successful Market Snapshot on Home

**Files:**
- Create: `backend/app/services/market_intelligence_read_service.py`
- Modify: `backend/app/services/home_feed.py`
- Test: `backend/tests/test_market_intelligence_home_read.py`
- Test: `backend/tests/test_home_feed.py`

- [ ] **Step 1: Write failing read service test**

Create `backend/tests/test_market_intelligence_home_read.py`:

```python
from datetime import date, datetime

from app.models import MarketIntelligenceSnapshot
from app.services.market_intelligence_read_service import load_latest_market_intelligence_for_home


def test_load_latest_market_intelligence_for_home_skips_failed_snapshots(db_session):
    db_session.add(
        MarketIntelligenceSnapshot(
            snapshot_date=date(2026, 4, 26),
            generated_at=datetime(2026, 4, 26, 8, 0, 0),
            window_days=90,
            market_signal_payload={},
            report_payload={"headline": "failed"},
            status="failed",
            error_message="bad output",
        )
    )
    db_session.add(
        MarketIntelligenceSnapshot(
            snapshot_date=date(2026, 4, 25),
            generated_at=datetime(2026, 4, 25, 8, 0, 0),
            window_days=90,
            market_signal_payload={},
            report_payload={
                "headline": "AI infra is still the main signal",
                "narrative": "30d and 90d market snapshots show infrastructure hiring staying warm.",
                "primary_judgment": {"claim": "AI infra", "why_it_matters": "deployment", "confidence": "medium"},
                "perspectives": [],
                "trend_cards": [],
                "watchlist": [],
            },
            status="success",
        )
    )
    db_session.commit()

    intelligence = load_latest_market_intelligence_for_home(db_session)

    assert intelligence is not None
    assert intelligence["headline"] == "AI infra is still the main signal"
    assert intelligence["narrative"].startswith("30d and 90d")
    assert intelligence["analysis_version"] == "market-intelligence-v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_home_read.py
```

Expected: import failure for `market_intelligence_read_service`.

- [ ] **Step 3: Add read service**

Create `backend/app/services/market_intelligence_read_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot


def load_latest_market_intelligence_for_home(db: Session) -> dict | None:
    snapshot = (
        db.execute(
            select(MarketIntelligenceSnapshot)
            .where(MarketIntelligenceSnapshot.status == "success")
            .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
        )
        .scalars()
        .first()
    )
    if snapshot is None:
        return None

    report = dict(snapshot.report_payload or {})
    narrative = str(report.get("narrative") or "").strip()
    headline = str(report.get("headline") or "").strip()
    if not narrative or not headline:
        return None

    return {
        "narrative": narrative,
        "headline": headline,
        "summary": str(report.get("primary_judgment", {}).get("claim") or headline),
        "analysis_version": "market-intelligence-v1",
        "rule_version": "market-intelligence-v1",
        "window_start": None,
        "window_end": snapshot.snapshot_date.isoformat(),
        "generated_at": snapshot.generated_at.replace(microsecond=0).isoformat(),
        "findings": [card.get("judgment") for card in report.get("trend_cards", []) if isinstance(card, dict) and card.get("judgment")][:1],
        "actions": list(report.get("watchlist") or [])[:1],
    }
```

- [ ] **Step 4: Modify home feed fallback order**

In `backend/app/services/home_feed.py`, import:

```python
from app.services.market_intelligence_read_service import load_latest_market_intelligence_for_home
```

Inside `build_home_payload`, compute:

```python
    market_intelligence = load_latest_market_intelligence_for_home(db)
    intelligence = market_intelligence or build_intelligence_snapshot(day_payloads, meta, jobs=jobs)
```

Then pass `intelligence=intelligence` to `assemble_home_payload(...)`.

- [ ] **Step 5: Run home tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_home_read.py tests/test_home_feed.py tests/test_home_api.py
```

Expected: tests pass and `/api/v1/home` contract remains `{intelligence, meta, days}`.

---

### Task 8: Adjust Raw Job Retention to 30 Days

**Files:**
- Modify: `backend/app/services/job_upsert_service.py`
- Test: existing or new test in `backend/tests/test_job_upsert_service.py`

- [ ] **Step 1: Find existing upsert retention tests**

Run:

```powershell
cd F:\赏金猎人\backend
Get-ChildItem -Path tests -Recurse -File | Select-String -Pattern "WINDOW_DAYS|delete_out_of_window_jobs|upsert_jobs"
```

Expected: identify the test file that already covers retention. If no test exists, create `backend/tests/test_job_upsert_service.py`.

- [ ] **Step 2: Write or update failing retention test**

The test should create one job collected 31 days ago and one job collected 29 days ago, run `delete_out_of_window_jobs(db_session)`, and assert only the 31-day-old job is deleted.

Expected assertion shape:

```python
remaining_titles = {job.title for job in db_session.query(Job).all()}
assert remaining_titles == {"fresh enough"}
```

- [ ] **Step 3: Change retention window**

In `backend/app/services/job_upsert_service.py`, change:

```python
WINDOW_DAYS = 14
```

to:

```python
WINDOW_DAYS = 30
```

- [ ] **Step 4: Run retention tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_job_upsert_service.py
```

Expected: retention test passes.

---

### Task 9: Add Frontend Scroll Support for Long Narrative

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/components/IntelligencePanel.test.tsx`

- [ ] **Step 1: Add or update frontend test**

In `frontend/components/IntelligencePanel.test.tsx`, add a test that renders a long `narrative`, opens the intelligence paper, and asserts all text appears.

Expected test behavior:

```tsx
expect(screen.getByText(/90 天视角/)).toBeInTheDocument();
expect(container.querySelector(".intel-paper-copy")).toBeInTheDocument();
```

- [ ] **Step 2: Run frontend test**

Run:

```powershell
cd F:\赏金猎人\frontend
npm test
```

Expected: the render test passes and confirms the long report text is present. CSS behavior is verified by the build and browser check after the style change.

- [ ] **Step 3: Add stable scroll styling**

In `frontend/app/globals.css`, update `.intel-paper-copy`:

```css
.intel-paper-copy {
  max-height: min(360px, 52vh);
  overflow-y: auto;
  scrollbar-gutter: stable;
}
```

If the current `.intel-paper-copy` block already exists, merge these declarations into it without duplicating the selector.

- [ ] **Step 4: Run frontend verification**

Run:

```powershell
cd F:\赏金猎人\frontend
npm test
npm run build
```

Expected: tests and production build pass.

---

### Task 10: PostgreSQL and Release Gate Verification

**Files:**
- Modify: `deploy/README.md`
- Modify: `deploy/ops-runbook.md`

- [ ] **Step 1: Run backend targeted tests**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q tests/test_market_intelligence_snapshot_model.py tests/test_market_intelligence_signals.py tests/test_market_intelligence_report.py tests/test_market_intelligence_snapshot_service.py tests/test_market_intelligence_home_read.py tests/test_daily_bounty_service.py tests/test_home_feed.py tests/test_home_api.py
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run full local backend and frontend verification**

Run:

```powershell
cd F:\赏金猎人\backend
pytest -q
cd F:\赏金猎人\frontend
npm test
npm run build
```

Expected: all pass.

- [ ] **Step 3: Run local PostgreSQL smoke**

With local `.env` pointing to local PostgreSQL, run:

```powershell
cd F:\赏金猎人\backend
python -c "from app.db.init_db import init_db; init_db()"
python -m app.cli.daily_bounty
```

Expected: new `market_intelligence_snapshots` table exists and receives either a `success` or `failed` row without leaking secrets.

- [ ] **Step 4: Confirm git hygiene**

Run:

```powershell
cd F:\赏金猎人
git status --short
git diff --check
```

Expected: no `.env`, database files, cache directories, `.next*`, `node_modules`, or build output staged.

- [ ] **Step 5: Production release actions**

On the server, after code is merged and pulled:

```bash
cd /opt/bounty-pool/app/backend
source /opt/bounty-pool/venv/bin/activate
python -c "from app.db.init_db import init_db; init_db()"
sudo systemctl restart bounty-pool
curl -f http://127.0.0.1:8000/health
python -m app.cli.daily_bounty
curl -f https://api.talentsignal.cloud/api/v1/home
```

Expected: service is healthy, `daily_bounty` completes, and `/api/v1/home` returns an `intelligence.narrative` that does not contain source websites, job links, full JD, bounty, claims, BD, or client-development language.

## Rollback Notes

- If only report generation fails, keep the service online and let home fall back to the latest successful snapshot or old rule intelligence.
- If `daily_bounty` fails because of market intelligence, rollback the code or disable the call path; do not delete production snapshot data during an incident.
- If the new table exists and code is rolled back, leave the table in place. An unused table is safer than dropping production data during emergency rollback.
- If a future version modifies existing tables, prepare explicit SQL migration and rollback commands before deployment.
