# Talentverse Report API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global-only Talentverse report variant pipeline that rewrites successful Talent Signal living reports into SEO/GEO-ready Talentverse research reports, stores them independently, and exposes them through authenticated APIs without changing existing `/api/v1/home` or `/api/v1/home/japan`.

**Architecture:** Keep `MarketIntelligenceSnapshot` as the raw report source of truth. Add a separate `talentverse_reports` table plus focused generation/read/API services. The 3-day living report refresh flow calls Talentverse generation only after a global raw report succeeds; failures create `failed` Talentverse rows and do not affect the original product.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic v2, existing `llm_client.request_structured_json`, existing `init_db` lightweight schema creation, pytest.

**Runtime Tradeoff:** First version runs the Talentverse rewrite synchronously inside the scheduled report refresh path after the raw report has already succeeded. This can add up to the configured Talentverse LLM timeout to the cron runtime, but the call is isolated so timeout, validation, or persistence failures never change the raw report result or home API behavior.

---

## Scope

### In Scope

- Generate Talentverse report variants only for `region="global"` in this version.
- Store Talentverse reports in a new table: `talentverse_reports`.
- Expose authenticated APIs:
  - `GET /api/v1/talentverse/reports`
  - `GET /api/v1/talentverse/reports/{slug}`
- Return only `status="published"` from the APIs.
- Keep `draft` and `failed` hidden from the public API.
- Preserve existing raw report and home APIs unchanged.
- Use structured JSON validation before publishing.

### Out of Scope

- Japan report generation.
- Admin UI for manual publishing.
- Revalidate webhook.
- Full distributed rate limiting across multiple app processes.
- Changing cron schedule.
- Changing existing raw report prompt.

## Existing Context

- Current public home APIs live in `backend/app/api/home.py`.
- Existing raw living reports are stored in `backend/app/models/market_intelligence_snapshot.py`.
- Raw report generation lives in `backend/app/services/market_intelligence_living_report_service.py`.
- The 3-day refresh gate lives in `backend/app/services/market_intelligence_living_refresh_service.py`.
- Existing LLM JSON helper is `backend/app/services/llm_client.py`.
- Existing app router wiring is in `backend/app/main.py`.
- Existing DB table creation is handled by `backend/app/db/init_db.py`.

## File Map

### Create

- `backend/app/models/talentverse_report.py`
  - SQLAlchemy model for independent Talentverse report variants.
- `backend/app/schemas/talentverse_report.py`
  - Pydantic response models for list/detail API.
- `backend/app/api/talentverse_auth.py`
  - Bearer token dependency and simple in-process 60/minute rate limiter.
- `backend/app/api/talentverse_reports.py`
  - API router for list/detail endpoints.
- `backend/app/services/talentverse_report_generation.py`
  - Prompt, parsing, validation, slug generation, and persistence orchestration.
- `backend/app/services/talentverse_report_read_service.py`
  - Read-only listing/detail query logic.
- `backend/tests/test_talentverse_report_model.py`
  - Model/init DB coverage.
- `backend/tests/test_talentverse_report_generation.py`
  - Generation, validation, failure, idempotency coverage.
- `backend/tests/test_talentverse_report_api.py`
  - Auth, list, detail, filtering, cursor coverage.

### Modify

- `backend/app/models/__init__.py`
  - Export `TalentverseReport`.
- `backend/app/db/init_db.py`
  - Import model so `Base.metadata.create_all` creates table.
- `backend/app/core/config.py`
  - Add `reports_api_token` setting.
- `backend/.env.example`
  - Document `REPORTS_API_TOKEN`.
- `backend/app/services/market_intelligence_living_refresh_service.py`
  - Call Talentverse generation after successful global living report generation.
- `backend/app/main.py`
  - Include the new Talentverse router under `/api/v1`.
- `backend/tests/conftest.py`
  - Import the new model module in the model-load tuple if needed by test DB setup.
- `backend/tests/test_market_intelligence_living_refresh.py`
  - Verify refresh calls Talentverse generation only for successful global reports.

## Data Contract

### DB Columns

`talentverse_reports` columns:

- `id`: integer primary key.
- `raw_report_id`: integer, indexed, unique, references `market_intelligence_snapshots.id` by convention.
- `slug`: string, unique, indexed.
- `region`: string, indexed, first version only writes `global`.
- `locale`: string, first version writes `zh-CN`.
- `title`: string.
- `status`: string, indexed, one of `draft`, `published`, `failed`.
- `published_at`: datetime, nullable for failed rows.
- `updated_at`: datetime, required.
- `version`: integer.
- `payload`: JSON, full public report document.
- `error_message`: text, nullable.
- `created_at`: datetime, required.

### API ID Formatting

- Report ID returned to clients: `tv-report-{talentverse_reports.id}`.
- Raw report ID returned to clients: `market-intelligence-snapshot-{raw_report_id}`.
- Internal DB IDs stay integers.

### Slug Format

For global reports:

```text
global-talentverse-report-{snapshot_date}-v{living_report.version}
```

Example:

```text
global-talentverse-report-2026-05-24-v6
```

### Publish Rules

- Publish only when LLM output passes strict validation.
- Create or update a `failed` row when LLM generation or validation fails.
- Do not publish rows with forbidden raw fields in payload text or keys.
- Do not generate for `region="japan"` in this version.

---

## Task 1: Add Talentverse Report Model and DB Wiring

**Files:**
- Create: `backend/app/models/talentverse_report.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/init_db.py`
- Test: `backend/tests/test_talentverse_report_model.py`
- Modify if needed: `backend/tests/conftest.py`

- [ ] **Step 1: Write failing model round-trip test**

Create `backend/tests/test_talentverse_report_model.py`:

```python
from datetime import datetime

from sqlalchemy import inspect, select

from app.db.database import engine
from app.db.init_db import init_db
from app.models import TalentverseReport


def test_talentverse_report_table_created_by_init_db():
    init_db()

    inspector = inspect(engine)

    assert "talentverse_reports" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("talentverse_reports")}
    assert {
        "id",
        "raw_report_id",
        "slug",
        "region",
        "locale",
        "title",
        "status",
        "published_at",
        "updated_at",
        "version",
        "payload",
        "error_message",
        "created_at",
    }.issubset(columns)


def test_talentverse_report_round_trips_payload(db_session):
    now = datetime(2026, 5, 25, 10, 30, 0)
    report = TalentverseReport(
        raw_report_id=23,
        slug="global-talentverse-report-2026-05-24-v6",
        region="global",
        locale="zh-CN",
        title="全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        status="published",
        published_at=now,
        updated_at=now,
        version=6,
        payload={"title": "全球招聘活动短期收缩", "keySignals": [{"signal": "短期收缩"}]},
        created_at=now,
    )
    db_session.add(report)
    db_session.commit()

    loaded = db_session.execute(select(TalentverseReport)).scalar_one()

    assert loaded.raw_report_id == 23
    assert loaded.slug == "global-talentverse-report-2026-05-24-v6"
    assert loaded.payload["keySignals"][0]["signal"] == "短期收缩"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_model.py -q
```

Expected: failure importing `TalentverseReport`.

- [ ] **Step 3: Create SQLAlchemy model**

Create `backend/app/models/talentverse_report.py`:

```python
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TalentverseReport(Base):
    __tablename__ = "talentverse_reports"
    __table_args__ = (
        UniqueConstraint("raw_report_id", name="uq_talentverse_reports_raw_report_id"),
        UniqueConstraint("slug", name="uq_talentverse_reports_slug"),
        CheckConstraint("status IN ('draft', 'published', 'failed')", name="ck_talentverse_reports_status"),
        Index(
            "ix_talentverse_reports_public_feed",
            "status",
            "region",
            "locale",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_report_id: Mapped[int] = mapped_column(Integer, index=True)
    slug: Mapped[str] = mapped_column(String(255), index=True)
    region: Mapped[str] = mapped_column(String(32), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 4: Export and import model**

Modify `backend/app/models/__init__.py`:

```python
from app.models.company_daily_summary import CompanyDailySummary
from app.models.intelligence_snapshot import IntelligenceSnapshot
from app.models.job import Job
from app.models.job_claim import JobClaim
from app.models.market_intelligence_fact import MarketIntelligenceFact
from app.models.market_intelligence_snapshot import MarketIntelligenceSnapshot
from app.models.talentverse_report import TalentverseReport

__all__ = [
    "CompanyDailySummary",
    "IntelligenceSnapshot",
    "Job",
    "JobClaim",
    "MarketIntelligenceFact",
    "MarketIntelligenceSnapshot",
    "TalentverseReport",
]
```

Modify `backend/app/db/init_db.py` imports and `_` tuple:

```python
from app.models import (
    company_daily_summary,
    intelligence_snapshot,
    job,
    job_claim,
    market_intelligence_fact,
    market_intelligence_snapshot,
    talentverse_report,
)
```

```python
    _ = (
        job,
        company_daily_summary,
        job_claim,
        intelligence_snapshot,
        market_intelligence_fact,
        market_intelligence_snapshot,
        talentverse_report,
    )
```

If `backend/tests/conftest.py` has an explicit model-load tuple, add `talentverse_report` there using the same pattern.

- [ ] **Step 5: Run model tests**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_model.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit model task**

Run:

```bash
git add backend/app/models/talentverse_report.py backend/app/models/__init__.py backend/app/db/init_db.py backend/tests/test_talentverse_report_model.py backend/tests/conftest.py
git commit -m "feat: add talentverse report model"
```

---

## Task 2: Add Talentverse Report Generation and Validation Service

**Files:**
- Create: `backend/app/services/talentverse_report_generation.py`
- Test: `backend/tests/test_talentverse_report_generation.py`

- [ ] **Step 1: Write failing tests for prompt generation, validation, success, failure, and idempotency**

Create `backend/tests/test_talentverse_report_generation.py`:

```python
from datetime import date, datetime

from sqlalchemy import select

from app.models import MarketIntelligenceSnapshot, TalentverseReport
from app.services import talentverse_report_generation as service


def _raw_snapshot(*, region: str = "global", version: int = 6) -> MarketIntelligenceSnapshot:
    generated_at = datetime(2026, 5, 24, 15, 30, 4)
    return MarketIntelligenceSnapshot(
        id=23,
        region=region,
        snapshot_date=date(2026, 5, 24),
        generated_at=generated_at,
        window_days=180,
        status="success",
        market_signal_payload={
            "data_quality": {"sample_count": 1189},
            "market_windows": {"window_days": 180},
        },
        report_payload={
            "living_report": {
                "kind": "living_market_report",
                "schema_version": "living-market-report-v1",
                "headline": "全球招聘市场短期显收缩，AI与数据核心岗位韧性依旧",
                "version": version,
                "mode": "incremental_update",
                "previous_snapshot_id": 20,
                "seed_window_days": 180,
                "generated_at": generated_at.isoformat(),
                "executive_summary": "近7天岗位数较30天下降67.1%，但AI、数据和资深技术岗位仍保持韧性。",
                "sections": [
                    {
                        "section_id": "market_structure",
                        "title": "市场结构",
                        "body": "AI/算法与数据岗位合计占比68.5%，数据岗位占比上升。",
                        "claim_ids": ["c1"],
                    }
                ],
                "claims": [
                    {
                        "claim_id": "c1",
                        "previous_claim_id": None,
                        "status": "new",
                        "claim": "近7天岗位数较30天下降67.1%。",
                        "confidence": "high",
                        "evidence_ids": ["fact-1561", "fact-1560"],
                        "evidence_notes": [
                            "fact-1561: Technical Program Manager III, ML Infrastructure Resource Management, Google Cloud",
                            "fact-1560: Software Engineer III, AI/ML, Google Workspace",
                        ],
                        "change_reason": "7d_vs_30d ratio=0.3287。",
                    }
                ],
                "watchlist": [
                    {
                        "topic": "数据工程和数据基础设施岗位是否继续扩张",
                        "why_watch": "如果数据岗位继续超过 AI/算法岗位，说明投入重心可能转向数据资产。",
                        "evidence_ids": ["fact-1561"],
                    }
                ],
                "data_quality": {
                    "sample_count": 1189,
                    "baseline_note": "当前可见岗位的历史基线，不代表完整真实半年历史。",
                },
            }
        },
    )


def _valid_talentverse_payload() -> dict:
    return {
        "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        "subtitle": "基于 Talent Signal 公开招聘信号样本生成的 Talentverse 前沿科技招聘市场观察",
        "executiveSummary": "过去 180 天的公开招聘信号显示，全球招聘活动出现短期收缩，但 AI、数据和资深技术岗位仍保持结构性需求。Talentverse 将这一变化理解为企业从广泛扩张转向更谨慎的关键岗位筛选。",
        "keySignals": [
            {
                "signal": "全球招聘活动短期收缩",
                "data": "近 7 天岗位数较 30 天下降 67.1%。",
                "interpretation": "Talentverse 将这理解为从广泛扩张招聘转向更谨慎的关键岗位筛选。",
                "hiringImplication": "企业仍在招聘，但更倾向于投入能直接影响基础设施、数据资产和 AI 应用落地的岗位。",
                "confidence": "high",
                "evidenceRefs": ["fact-1561", "fact-1560"],
            }
        ],
        "marketStructure": {
            "body": "市场结构显示，AI / 算法与数据岗位仍是前沿科技招聘中的核心需求。",
            "metrics": [
                {
                    "label": "AI / 算法 + 数据岗位占比",
                    "value": "68.5%",
                    "description": "招聘需求仍集中在技术和数据能力上。",
                }
            ],
        },
        "demandShift": {
            "body": "短期窗口显示岗位数量下降，但长期窗口仍能看到 AI、数据和资深技术岗位的稳定存在。",
            "metrics": [
                {
                    "label": "7 天岗位数变化",
                    "value": "-67.1%",
                    "description": "相对 30 天窗口出现明显短期收缩。",
                }
            ],
        },
        "talentStrategyImplications": [
            {
                "title": "关键岗位优先级应高于岗位数量扩张",
                "body": "企业应优先确认哪些岗位真正影响产品、数据基础设施、AI 应用落地和组织执行。",
            }
        ],
        "risksAndWatchlist": [
            {
                "topic": "数据工程和数据基础设施岗位是否继续扩张",
                "reason": "如果数据岗位继续超过 AI / 算法岗位，说明企业的人才投入重心可能从模型能力转向数据资产和工程化能力。",
                "evidenceRefs": ["fact-1561"],
            }
        ],
        "talentverseView": "Talentverse 认为，这轮变化说明前沿科技招聘市场正在从数量扩张转向高确定性招聘。",
        "methodologyNote": {
            "sampleCount": 1189,
            "windowDays": 180,
            "body": "数据来源为 Talent Signal，基于公开招聘信号和结构化样本，不代表完整市场全量。",
        },
        "faq": [
            {
                "question": "这篇报告对 AI 团队招聘意味着什么？",
                "answer": "AI 团队应关注数据基础设施、AI 应用落地和资深技术岗位，而不是只看岗位数量。",
            }
        ],
        "glossaryTerms": [
            {
                "term": "高确定性招聘",
                "definition": "一种优先关注证据质量、岗位影响和长期匹配度的关键人才招聘方式。",
            }
        ],
        "evidenceRefs": [
            {
                "id": "fact-1561",
                "note": "Technical Program Manager III, ML Infrastructure Resource Management, Google Cloud",
                "confidence": "high",
            }
        ],
        "seo": {
            "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
            "description": "Talentverse 前沿科技招聘报告：全球招聘活动短期收缩，但 AI、数据与资深技术岗位需求保持韧性。",
            "keywords": ["frontier tech hiring", "AI-native talent intelligence", "高确定性招聘"],
        },
    }


def test_build_slug_uses_region_date_and_version():
    snapshot = _raw_snapshot()

    assert service.build_talentverse_slug(snapshot) == "global-talentverse-report-2026-05-24-v6"


def test_validate_talentverse_payload_rejects_forbidden_raw_fields():
    payload = _valid_talentverse_payload()
    payload["canonical_url"] = "https://example.com/raw-job"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "forbidden field" in str(exc)
    else:
        raise AssertionError("expected forbidden field validation failure")


def test_validate_talentverse_payload_rejects_forbidden_raw_text():
    payload = _valid_talentverse_payload()
    payload["talentverseView"] = "不要暴露 canonical_url 或 full_description。"

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "forbidden text" in str(exc)
    else:
        raise AssertionError("expected forbidden text validation failure")


def test_validate_talentverse_payload_rejects_invalid_nested_key_signal():
    payload = _valid_talentverse_payload()
    del payload["keySignals"][0]["hiringImplication"]

    try:
        service.validate_talentverse_payload(payload, raw_snapshot=_raw_snapshot())
    except service.TalentverseReportError as exc:
        assert "hiringImplication" in str(exc)
    else:
        raise AssertionError("expected nested schema validation failure")


def test_generate_talentverse_report_publishes_valid_payload(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    payload = _valid_talentverse_payload()

    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: service.json.dumps(payload))

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "published"
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert report.raw_report_id == snapshot.id
    assert report.slug == "global-talentverse-report-2026-05-24-v6"
    assert report.status == "published"
    assert report.payload["source"]["name"] == "Talent Signal"
    assert report.payload["status"] == "published"


def test_generate_talentverse_report_records_failed_without_raising(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()

    def fail_request(messages, timeout_seconds=None):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(service, "request_structured_json", fail_request)

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "failed"
    report = db_session.execute(select(TalentverseReport)).scalar_one()
    assert report.status == "failed"
    assert "provider unavailable" in report.error_message


def test_generate_talentverse_report_skips_japan_in_first_version(db_session, monkeypatch):
    snapshot = _raw_snapshot(region="japan")
    db_session.add(snapshot)
    db_session.commit()

    result = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    assert result["status"] == "skipped"
    assert db_session.execute(select(TalentverseReport)).scalars().all() == []


def test_generate_talentverse_report_is_idempotent_for_published_raw_report(db_session, monkeypatch):
    snapshot = _raw_snapshot()
    db_session.add(snapshot)
    db_session.commit()
    payload = _valid_talentverse_payload()
    monkeypatch.setattr(service, "request_structured_json", lambda messages, timeout_seconds=None: service.json.dumps(payload))

    first = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)
    second = service.generate_talentverse_report_for_snapshot(db_session, raw_snapshot_id=snapshot.id)

    reports = db_session.execute(select(TalentverseReport)).scalars().all()
    assert first["status"] == "published"
    assert second["status"] == "published"
    assert len(reports) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_generation.py -q
```

Expected: failure importing `talentverse_report_generation`.

- [ ] **Step 3: Implement service skeleton, constants, slug, parsing, and validation**

Create `backend/app/services/talentverse_report_generation.py`:

```python
import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketIntelligenceSnapshot, TalentverseReport
from app.services.llm_client import request_structured_json
from app.services.region import GLOBAL_REGION

TALENTVERSE_REPORT_STATUS_DRAFT = "draft"
TALENTVERSE_REPORT_STATUS_PUBLISHED = "published"
TALENTVERSE_REPORT_STATUS_FAILED = "failed"
TALENTVERSE_LOCALE = "zh-CN"
TALENTVERSE_SOURCE_NAME = "Talent Signal"
TALENTVERSE_SOURCE_URL = "https://talentsignal.cloud"
TALENTVERSE_CATEGORY = "market-intelligence"
TALENTVERSE_TAGS = ["global", "talent-strategy", "ai", "data"]
TALENTVERSE_LLM_TIMEOUT_SECONDS = 120
DB_CREDENTIAL_URL_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@[^\s]+",
    re.IGNORECASE,
)
OPENAI_KEY_PATTERN = re.compile(r"sk-[^\s,;]+", re.IGNORECASE)
KEY_VALUE_SECRET_PATTERN = re.compile(
    r"\b([a-z0-9_]*(?:api_key|token|password))\s*([=:])\s*([^\s,;]+)",
    re.IGNORECASE,
)
AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\bAuthorization\s*:\s*Bearer\s+[^\s,;]+",
    re.IGNORECASE,
)
FORBIDDEN_FIELDS = {
    "canonical_url",
    "source_name",
    "source_url",
    "job_url",
    "full_description",
    "description",
    "bounty_grade",
    "claimed_names",
    "claim_status",
    "bd_entry",
    "signal_tags",
}
FORBIDDEN_TEXT = (
    "招聘中介",
    "简历推荐",
    "海量人才库",
    "精准匹配",
    "AI-powered headhunter",
    "传统猎头",
    "全球领先",
    "赋能企业",
    "生态闭环",
    "一站式解决方案",
    "canonical_url",
    "source_name",
    "full_description",
    "job_url",
)


class TalentverseReportError(Exception):
    pass


def sanitize_talentverse_error(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    message = DB_CREDENTIAL_URL_PATTERN.sub("[redacted]", message)
    message = AUTHORIZATION_BEARER_PATTERN.sub("Authorization: Bearer [redacted]", message)
    message = OPENAI_KEY_PATTERN.sub("[redacted]", message)
    return KEY_VALUE_SECRET_PATTERN.sub(_redact_key_value_secret, message)


def _redact_key_value_secret(match: re.Match) -> str:
    separator = match.group(2)
    if separator == ":":
        return f"{match.group(1)}: [redacted]"
    return f"{match.group(1)}=[redacted]"


def build_talentverse_slug(snapshot: MarketIntelligenceSnapshot) -> str:
    living_report = _living_report(snapshot)
    version = living_report.get("version")
    if not isinstance(version, int):
        raise TalentverseReportError("living_report.version must be an integer")
    return f"{snapshot.region}-talentverse-report-{snapshot.snapshot_date.isoformat()}-v{version}"


def generate_talentverse_report_for_snapshot(db: Session, *, raw_snapshot_id: int) -> dict[str, Any]:
    snapshot = db.get(MarketIntelligenceSnapshot, raw_snapshot_id)
    if snapshot is None:
        return {"status": "skipped", "reason": "raw_report_missing"}
    if snapshot.region != GLOBAL_REGION:
        return {"status": "skipped", "reason": "unsupported_region"}
    if snapshot.status != "success":
        return {"status": "skipped", "reason": "raw_report_not_success"}

    try:
        existing = _load_existing_report(db, raw_report_id=snapshot.id)
        if existing is not None and existing.status == TALENTVERSE_REPORT_STATUS_PUBLISHED:
            return {"status": "published", "report_id": existing.id, "slug": existing.slug}

        slug = build_talentverse_slug(snapshot)
        now = snapshot.generated_at.replace(microsecond=0)
        content = request_structured_json(
            [
                {"role": "system", "content": build_talentverse_system_prompt()},
                {"role": "user", "content": build_talentverse_user_prompt(snapshot)},
            ],
            timeout_seconds=TALENTVERSE_LLM_TIMEOUT_SECONDS,
        )
        payload = parse_talentverse_payload(content)
        validate_talentverse_payload(payload, raw_snapshot=snapshot)
        final_payload = normalize_talentverse_payload(payload, raw_snapshot=snapshot, slug=slug)
        report = _upsert_report(
            db,
            existing=existing,
            snapshot=snapshot,
            slug=slug,
            status=TALENTVERSE_REPORT_STATUS_PUBLISHED,
            payload=final_payload,
            error_message=None,
            published_at=now,
        )
        return {"status": "published", "report_id": report.id, "slug": report.slug}
    except Exception as exc:  # noqa: BLE001
        error_message = sanitize_talentverse_error(exc)
        try:
            report = _record_failed_report(db, snapshot=snapshot, error_message=error_message)
        except Exception as record_exc:  # noqa: BLE001
            db.rollback()
            return {
                "status": "failed",
                "error": error_message,
                "record_error": sanitize_talentverse_error(record_exc),
            }
        return {"status": "failed", "report_id": report.id, "error": error_message}


def build_talentverse_system_prompt() -> str:
    return (
        "You transform a sanitized Talent Signal living market report into a Talentverse website research report. "
        "Return only one JSON object. Do not return Markdown or HTML. "
        "Talentverse is an AI-native talent intelligence and executive recruiting firm helping frontier technology "
        "and new economy companies identify, evaluate, and hire mission-critical talent. "
        "Write in natural Chinese. Use phrases such as AI 原生人才战略, 人才判断, 人才研究, 高确定性招聘, 关键岗位, "
        "前沿科技招聘, 技术与产品人才, 新经济团队. "
        "Do not use 招聘中介, 简历推荐, 海量人才库, 精准匹配, AI-powered headhunter, 传统猎头, 全球领先, "
        "赋能企业, 生态闭环, 一站式解决方案. "
        "Preserve key numbers, time windows, facts, confidence labels, and evidence references from the input. "
        "Do not invent data. Every important judgment must include hiringImplication. "
        "Do not expose raw job links, full JD, source_name, canonical_url, full_description, job_url, or similar fields. "
        "Generate fields exactly matching this schema: title, subtitle, executiveSummary, keySignals, marketStructure, "
        "demandShift, talentStrategyImplications, risksAndWatchlist, talentverseView, methodologyNote, faq, "
        "glossaryTerms, evidenceRefs, seo. "
        "keySignals items require signal, data, interpretation, hiringImplication, confidence, evidenceRefs. "
        "marketStructure and demandShift require body and metrics. "
        "talentStrategyImplications require title and body. "
        "risksAndWatchlist require topic, reason, evidenceRefs. "
        "methodologyNote requires sampleCount, windowDays, body. "
        "faq requires question and answer. glossaryTerms require term and definition. "
        "evidenceRefs require id, note, confidence. seo requires title, description, keywords. "
        "The report must be useful for SEO, GEO, and AI citation: include stable definitions, clear claims, and evidence IDs."
    )


def build_talentverse_user_prompt(snapshot: MarketIntelligenceSnapshot) -> str:
    living_report = _living_report(snapshot)
    input_payload = {
        "rawReportId": f"market-intelligence-snapshot-{snapshot.id}",
        "region": snapshot.region,
        "locale": TALENTVERSE_LOCALE,
        "snapshotDate": snapshot.snapshot_date.isoformat(),
        "generatedAt": snapshot.generated_at.replace(microsecond=0).isoformat(),
        "windowDays": snapshot.window_days,
        "source": {
            "name": TALENTVERSE_SOURCE_NAME,
            "url": TALENTVERSE_SOURCE_URL,
            "generatedAt": snapshot.generated_at.replace(microsecond=0).isoformat(),
            "version": living_report.get("version"),
        },
        "livingReport": living_report,
        "dataQuality": living_report.get("data_quality"),
    }
    return json.dumps(input_payload, ensure_ascii=False, sort_keys=True)


def parse_talentverse_payload(content: str) -> dict:
    try:
        payload = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise TalentverseReportError("talentverse response must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise TalentverseReportError("talentverse response must be a JSON object")
    return payload


def validate_talentverse_payload(payload: dict, *, raw_snapshot: MarketIntelligenceSnapshot) -> None:
    required_fields = {
        "title",
        "subtitle",
        "executiveSummary",
        "keySignals",
        "marketStructure",
        "demandShift",
        "talentStrategyImplications",
        "risksAndWatchlist",
        "talentverseView",
        "methodologyNote",
        "faq",
        "glossaryTerms",
        "evidenceRefs",
        "seo",
    }
    missing = sorted(required_fields - payload.keys())
    if missing:
        raise TalentverseReportError(f"missing required fields: {', '.join(missing)}")
    _reject_forbidden_fields(payload)
    _reject_forbidden_text(payload)
    _require_non_empty_text(payload, "title")
    _require_non_empty_text(payload, "subtitle")
    _require_non_empty_text(payload, "executiveSummary")
    _require_non_empty_list(payload, "keySignals")
    _validate_key_signal_items(payload["keySignals"])
    _validate_section_object(payload.get("marketStructure"), field="marketStructure")
    _validate_section_object(payload.get("demandShift"), field="demandShift")
    _require_non_empty_list(payload, "talentStrategyImplications")
    _validate_text_object_items(
        payload["talentStrategyImplications"],
        field="talentStrategyImplications",
        required_text_fields=("title", "body"),
    )
    _require_non_empty_list(payload, "risksAndWatchlist")
    _validate_text_object_items(
        payload["risksAndWatchlist"],
        field="risksAndWatchlist",
        required_text_fields=("topic", "reason"),
        optional_list_fields=("evidenceRefs",),
    )
    _require_non_empty_text(payload, "talentverseView")
    _require_non_empty_list(payload, "faq")
    _validate_text_object_items(payload["faq"], field="faq", required_text_fields=("question", "answer"))
    _require_non_empty_list(payload, "glossaryTerms")
    _validate_text_object_items(payload["glossaryTerms"], field="glossaryTerms", required_text_fields=("term", "definition"))
    _require_non_empty_list(payload, "evidenceRefs")
    _validate_text_object_items(payload["evidenceRefs"], field="evidenceRefs", required_text_fields=("id", "note", "confidence"))
    methodology = payload.get("methodologyNote")
    if not isinstance(methodology, dict):
        raise TalentverseReportError("methodologyNote must be an object")
    if methodology.get("sampleCount") is None:
        raise TalentverseReportError("methodologyNote.sampleCount is required")
    if methodology.get("windowDays") != raw_snapshot.window_days:
        raise TalentverseReportError("methodologyNote.windowDays must match raw snapshot")
    _require_non_empty_text(methodology, "body")
    seo = payload.get("seo")
    if not isinstance(seo, dict):
        raise TalentverseReportError("seo must be an object")
    _require_non_empty_text(seo, "title")
    _require_non_empty_text(seo, "description")
    if not isinstance(seo.get("keywords"), list) or not seo["keywords"]:
        raise TalentverseReportError("seo.keywords must be a non-empty list")


def normalize_talentverse_payload(payload: dict, *, raw_snapshot: MarketIntelligenceSnapshot, slug: str) -> dict:
    living_report = _living_report(raw_snapshot)
    generated_at = raw_snapshot.generated_at.replace(microsecond=0).isoformat()
    version = living_report["version"]
    return {
        "id": None,
        "rawReportId": f"market-intelligence-snapshot-{raw_snapshot.id}",
        "slug": slug,
        "region": raw_snapshot.region,
        "locale": TALENTVERSE_LOCALE,
        "title": payload["title"].strip(),
        "subtitle": payload["subtitle"].strip(),
        "executiveSummary": payload["executiveSummary"].strip(),
        "keySignals": payload["keySignals"],
        "marketStructure": payload["marketStructure"],
        "demandShift": payload["demandShift"],
        "talentStrategyImplications": payload["talentStrategyImplications"],
        "risksAndWatchlist": payload["risksAndWatchlist"],
        "talentverseView": payload["talentverseView"].strip(),
        "methodologyNote": payload["methodologyNote"],
        "faq": payload["faq"],
        "glossaryTerms": payload["glossaryTerms"],
        "evidenceRefs": payload["evidenceRefs"],
        "source": {
            "name": TALENTVERSE_SOURCE_NAME,
            "url": TALENTVERSE_SOURCE_URL,
            "generatedAt": generated_at,
            "version": version,
        },
        "seo": payload["seo"],
        "status": TALENTVERSE_REPORT_STATUS_PUBLISHED,
        "publishedAt": generated_at,
        "updatedAt": generated_at,
        "version": version,
        "category": TALENTVERSE_CATEGORY,
        "tags": TALENTVERSE_TAGS,
    }


def _upsert_report(
    db: Session,
    *,
    existing: TalentverseReport | None,
    snapshot: MarketIntelligenceSnapshot,
    slug: str,
    status: str,
    payload: dict,
    error_message: str | None,
    published_at: datetime | None,
) -> TalentverseReport:
    living_report = _safe_living_report(snapshot)
    now = snapshot.generated_at.replace(microsecond=0)
    report = existing or TalentverseReport(raw_report_id=snapshot.id, created_at=now)
    report.slug = slug
    report.region = snapshot.region
    report.locale = TALENTVERSE_LOCALE
    report.title = payload.get("title") or living_report.get("headline") or "Talentverse Report"
    report.status = status
    report.published_at = published_at
    report.updated_at = now
    report.version = _safe_living_version(snapshot)
    report.payload = payload
    report.error_message = error_message
    db.add(report)
    db.commit()
    db.refresh(report)
    if report.payload and report.payload.get("id") is None:
        report.payload = {**report.payload, "id": f"tv-report-{report.id}"}
        db.add(report)
        db.commit()
        db.refresh(report)
    return report


def _record_failed_report(db: Session, *, snapshot: MarketIntelligenceSnapshot, error_message: str) -> TalentverseReport:
    existing = _load_existing_report(db, raw_report_id=snapshot.id)
    return _upsert_report(
        db,
        existing=existing,
        snapshot=snapshot,
        slug=_safe_slug(snapshot),
        status=TALENTVERSE_REPORT_STATUS_FAILED,
        payload={},
        error_message=error_message,
        published_at=None,
    )


def _load_existing_report(db: Session, *, raw_report_id: int) -> TalentverseReport | None:
    return db.execute(
        select(TalentverseReport).where(TalentverseReport.raw_report_id == raw_report_id)
    ).scalar_one_or_none()


def _safe_slug(snapshot: MarketIntelligenceSnapshot) -> str:
    try:
        return build_talentverse_slug(snapshot)
    except TalentverseReportError:
        return f"{snapshot.region}-talentverse-report-{snapshot.snapshot_date.isoformat()}-raw-{snapshot.id}-failed"


def _safe_living_report(snapshot: MarketIntelligenceSnapshot) -> dict:
    try:
        return _living_report(snapshot)
    except TalentverseReportError:
        return {}


def _safe_living_version(snapshot: MarketIntelligenceSnapshot) -> int:
    living_report = _safe_living_report(snapshot)
    version = living_report.get("version")
    return version if isinstance(version, int) else 0


def _living_report(snapshot: MarketIntelligenceSnapshot) -> dict:
    report_payload = snapshot.report_payload if isinstance(snapshot.report_payload, dict) else {}
    living_report = report_payload.get("living_report")
    if not isinstance(living_report, dict):
        raise TalentverseReportError("raw snapshot is missing living_report")
    if living_report.get("kind") != "living_market_report":
        raise TalentverseReportError("raw living_report kind is unsupported")
    return living_report


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return match.group(1).strip() if match else stripped


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_FIELDS:
                raise TalentverseReportError(f"forbidden field: {key}")
            _reject_forbidden_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_fields(item)


def _reject_forbidden_text(value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False)
    for token in FORBIDDEN_TEXT:
        if token in text:
            raise TalentverseReportError(f"forbidden text: {token}")


def _require_non_empty_text(payload: dict, field: str) -> None:
    if not isinstance(payload.get(field), str) or not payload[field].strip():
        raise TalentverseReportError(f"{field} must be non-empty text")


def _require_non_empty_list(payload: dict, field: str) -> None:
    if not isinstance(payload.get(field), list) or not payload[field]:
        raise TalentverseReportError(f"{field} must be a non-empty list")


def _validate_key_signal_items(items: list) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TalentverseReportError(f"keySignals[{index}] must be an object")
        for field in ("signal", "data", "interpretation", "hiringImplication", "confidence"):
            _require_non_empty_text(item, field)
        evidence_refs = item.get("evidenceRefs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise TalentverseReportError(f"keySignals[{index}].evidenceRefs must be a non-empty list")


def _validate_section_object(value: object, *, field: str) -> None:
    if not isinstance(value, dict):
        raise TalentverseReportError(f"{field} must be an object")
    _require_non_empty_text(value, "body")
    metrics = value.get("metrics")
    if not isinstance(metrics, list):
        raise TalentverseReportError(f"{field}.metrics must be a list")
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            raise TalentverseReportError(f"{field}.metrics[{index}] must be an object")
        for metric_field in ("label", "value", "description"):
            _require_non_empty_text(metric, metric_field)


def _validate_text_object_items(
    items: list,
    *,
    field: str,
    required_text_fields: tuple[str, ...],
    optional_list_fields: tuple[str, ...] = (),
) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TalentverseReportError(f"{field}[{index}] must be an object")
        for required_field in required_text_fields:
            _require_non_empty_text(item, required_field)
        for list_field in optional_list_fields:
            if list_field in item and not isinstance(item[list_field], list):
                raise TalentverseReportError(f"{field}[{index}].{list_field} must be a list")
```

- [ ] **Step 4: Run generation tests**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_generation.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit generation service task**

Run:

```bash
git add backend/app/services/talentverse_report_generation.py backend/tests/test_talentverse_report_generation.py
git commit -m "feat: generate talentverse report variants"
```

---

## Task 3: Hook Talentverse Generation Into Global Living Report Refresh

**Files:**
- Modify: `backend/app/services/market_intelligence_living_refresh_service.py`
- Modify: `backend/tests/test_market_intelligence_living_refresh.py`

- [ ] **Step 1: Add failing refresh integration tests**

Append tests to `backend/tests/test_market_intelligence_living_refresh.py`:

```python
def test_refresh_generates_talentverse_variant_after_successful_global_report(db_session, monkeypatch):
    calls = []

    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 101},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: calls.append(raw_snapshot_id) or {"status": "published", "report_id": 201},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert calls == [101]
    assert result["talentverse_report"] == {"status": "published", "report_id": 201}


def test_refresh_does_not_generate_talentverse_variant_for_japan(db_session, monkeypatch):
    calls = []

    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 102},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: calls.append(raw_snapshot_id) or {"status": "published"},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session, region="japan")

    assert calls == []
    assert "talentverse_report" not in result


def test_refresh_records_talentverse_failed_without_failing_raw_report(db_session, monkeypatch):
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 103},
    )
    monkeypatch.setattr(
        refresh_service,
        "generate_talentverse_report_for_snapshot",
        lambda db, raw_snapshot_id: {"status": "failed", "error": "provider unavailable"},
    )

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert result["status"] == "success"
    assert result["talentverse_report"] == {"status": "failed", "error": "provider unavailable"}


def test_refresh_catches_talentverse_exception_without_failing_raw_report(db_session, monkeypatch):
    monkeypatch.setattr(
        refresh_service,
        "backfill_market_intelligence_facts",
        lambda db, days, dry_run, collected_at, region, adapters=None: {"processed": 1},
    )
    monkeypatch.setattr(refresh_service, "load_latest_success_living_snapshot", lambda db, region, report_profile=None: None)
    monkeypatch.setattr(
        refresh_service,
        "generate_living_market_report",
        lambda db, mode, days, snapshot_date, clock, region: {"status": "success", "snapshot_id": 104},
    )

    def raise_from_talentverse(db, raw_snapshot_id):
        raise RuntimeError("unexpected talentverse failure")

    monkeypatch.setattr(refresh_service, "generate_talentverse_report_for_snapshot", raise_from_talentverse)

    result = refresh_service.refresh_living_market_report_if_due(db_session)

    assert result["status"] == "success"
    assert result["talentverse_report"]["status"] == "failed"
    assert "unexpected talentverse failure" in result["talentverse_report"]["error"]
```

- [ ] **Step 2: Run targeted refresh tests to verify failure**

Run:

```bash
cd backend
pytest tests/test_market_intelligence_living_refresh.py -q
```

Expected: new tests fail because `generate_talentverse_report_for_snapshot` is not imported/called.

- [ ] **Step 3: Modify refresh service**

Modify `backend/app/services/market_intelligence_living_refresh_service.py`:

```python
from app.services.talentverse_report_generation import (
    generate_talentverse_report_for_snapshot,
    sanitize_talentverse_error,
)
```

Add after `result = generate_living_market_report(...)`:

```python
    if result.get("status") == "success" and region == GLOBAL_REGION:
        snapshot_id = result.get("snapshot_id")
        if isinstance(snapshot_id, int):
            try:
                result["talentverse_report"] = generate_talentverse_report_for_snapshot(
                    db,
                    raw_snapshot_id=snapshot_id,
                )
            except Exception as exc:  # noqa: BLE001
                result["talentverse_report"] = {
                    "status": "failed",
                    "error": sanitize_talentverse_error(exc),
                }
```

Keep the existing `result["facts"] = fact_summary` after this block so the returned summary still contains facts.
This hook must stay only in the branch where a new raw report was generated. Do not change the existing skipped/not-due path, Japan path, or raw report failure behavior.

- [ ] **Step 4: Run refresh tests**

Run:

```bash
cd backend
pytest tests/test_market_intelligence_living_refresh.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit refresh integration**

Run:

```bash
git add backend/app/services/market_intelligence_living_refresh_service.py backend/tests/test_market_intelligence_living_refresh.py
git commit -m "feat: publish talentverse reports after raw refresh"
```

---

## Task 4: Add Authenticated Read APIs

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/app/api/talentverse_auth.py`
- Create: `backend/app/schemas/talentverse_report.py`
- Create: `backend/app/services/talentverse_report_read_service.py`
- Create: `backend/app/api/talentverse_reports.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_talentverse_report_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_talentverse_report_api.py`:

```python
from datetime import datetime, timedelta

from app.models import TalentverseReport


def _payload(*, slug: str, version: int, generated_at: datetime) -> dict:
    iso_time = generated_at.replace(microsecond=0).isoformat()
    return {
        "id": None,
        "rawReportId": f"market-intelligence-snapshot-{version}",
        "slug": slug,
        "region": "global",
        "locale": "zh-CN",
        "title": "全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        "subtitle": "基于 Talent Signal 公开招聘信号样本生成的 Talentverse 前沿科技招聘市场观察",
        "executiveSummary": "过去 180 天的公开招聘信号显示，全球招聘活动出现短期收缩。",
        "keySignals": [
            {
                "signal": "全球招聘活动短期收缩",
                "data": "近 7 天岗位数较 30 天下降 67.1%。",
                "interpretation": "Talentverse 将这理解为关键岗位筛选。",
                "hiringImplication": "企业更应聚焦关键岗位。",
                "confidence": "high",
                "evidenceRefs": ["fact-1561"],
            }
        ],
        "marketStructure": {"body": "市场结构正文", "metrics": []},
        "demandShift": {"body": "需求变化正文", "metrics": []},
        "talentStrategyImplications": [{"title": "关键岗位优先", "body": "企业应聚焦关键岗位。"}],
        "risksAndWatchlist": [{"topic": "数据岗位", "reason": "观察扩张趋势", "evidenceRefs": ["fact-1561"]}],
        "talentverseView": "Talentverse 判断正文。",
        "methodologyNote": {"sampleCount": 1189, "windowDays": 180, "body": "数据来源为 Talent Signal。"},
        "faq": [{"question": "这对 AI 团队意味着什么？", "answer": "聚焦关键岗位。"}],
        "glossaryTerms": [{"term": "高确定性招聘", "definition": "关注证据质量和岗位影响。"}],
        "evidenceRefs": [{"id": "fact-1561", "note": "sample evidence", "confidence": "high"}],
        "source": {"name": "Talent Signal", "url": "https://talentsignal.cloud", "generatedAt": iso_time, "version": version},
        "seo": {"title": "SEO title", "description": "SEO description", "keywords": ["AI"]},
        "status": "published",
        "publishedAt": iso_time,
        "updatedAt": iso_time,
        "version": version,
        "category": "market-intelligence",
        "tags": ["global", "talent-strategy"],
    }


def _add_report(db_session, *, slug: str, version: int, status: str = "published", updated_at: datetime | None = None):
    now = updated_at or datetime(2026, 5, 24, 15, 30, 4)
    report = TalentverseReport(
        raw_report_id=version,
        slug=slug,
        region="global",
        locale="zh-CN",
        title="全球招聘活动短期收缩，AI 与数据关键岗位需求保持韧性",
        status=status,
        published_at=now if status == "published" else None,
        updated_at=now,
        version=version,
        payload=_payload(slug=slug, version=version, generated_at=now),
        created_at=now,
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    report.payload = {**report.payload, "id": f"tv-report-{report.id}"}
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


def test_talentverse_reports_requires_bearer_token(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get("/api/v1/talentverse/reports")

    assert response.status_code == 401


def test_talentverse_reports_returns_503_when_token_is_not_configured(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", None)
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 503


def test_talentverse_reports_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")

    response = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 403


def test_talentverse_reports_lists_only_published_reports(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)
    _add_report(db_session, slug="failed-report", version=7, status="failed")
    _add_report(db_session, slug="draft-report", version=8, status="draft")

    response = client.get(
        "/api/v1/talentverse/reports?region=global&status=published&limit=20",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["slug"] == "global-talentverse-report-2026-05-24-v6"
    assert payload["items"][0]["keySignals"][0]["signal"] == "全球招聘活动短期收缩"
    assert payload["pageInfo"]["limit"] == 20


def test_talentverse_reports_rejects_invalid_cursor(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports?cursor=bad-cursor",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 422


def test_talentverse_reports_rejects_invalid_region(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")

    response = client.get(
        "/api/v1/talentverse/reports?region=unknown",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 422


def test_talentverse_reports_rate_limits_by_client_host(client, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    monkeypatch.setattr("app.api.talentverse_auth.RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr("app.api.talentverse_auth._REQUEST_LOG", {})

    first = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )
    second = client.get(
        "/api/v1/talentverse/reports",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_talentverse_reports_supports_updated_after_filter(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    old_time = datetime(2026, 5, 20, 10, 0, 0)
    new_time = old_time + timedelta(days=4)
    _add_report(db_session, slug="old-report", version=1, updated_at=old_time)
    _add_report(db_session, slug="new-report", version=2, updated_at=new_time)

    response = client.get(
        "/api/v1/talentverse/reports?updatedAfter=2026-05-21T00:00:00",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["new-report"]


def test_talentverse_report_detail_returns_full_payload(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="global-talentverse-report-2026-05-24-v6", version=6)

    response = client.get(
        "/api/v1/talentverse/reports/global-talentverse-report-2026-05-24-v6",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "global-talentverse-report-2026-05-24-v6"
    assert "marketStructure" in payload
    assert "faq" in payload
    assert payload["status"] == "published"


def test_talentverse_report_detail_hides_failed_report(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="failed-report", version=7, status="failed")

    response = client.get(
        "/api/v1/talentverse/reports/failed-report",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 404


def test_talentverse_report_detail_hides_draft_report(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.talentverse_auth.settings.reports_api_token", "secret-token")
    _add_report(db_session, slug="draft-report", version=8, status="draft")

    response = client.get(
        "/api/v1/talentverse/reports/draft-report",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_api.py -q
```

Expected: failure because API/router/auth/read service do not exist.

- [ ] **Step 3: Add config and `.env.example`**

Modify `backend/app/core/config.py` inside `Settings`:

```python
    reports_api_token: str | None = None
```

Modify `backend/.env.example`:

```text
REPORTS_API_TOKEN=
```

- [ ] **Step 4: Add auth dependency**

Create `backend/app/api/talentverse_auth.py`:

```python
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings

RATE_LIMIT_PER_MINUTE = 60
_REQUEST_LOG: dict[str, deque[datetime]] = defaultdict(deque)


def require_reports_api_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = settings.reports_api_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reports API token is not configured",
        )
    _enforce_rate_limit(request)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    provided_token = authorization.removeprefix("Bearer ").strip()
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")


def _enforce_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = client_host
    now = datetime.now()
    cutoff = now - timedelta(minutes=1)
    request_times = _REQUEST_LOG.setdefault(key, deque())
    while request_times and request_times[0] < cutoff:
        request_times.popleft()
    if len(request_times) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    request_times.append(now)
```

- [ ] **Step 5: Add response schemas**

Create `backend/app/schemas/talentverse_report.py`:

```python
from pydantic import BaseModel, Field


class TalentversePageInfo(BaseModel):
    limit: int
    nextCursor: str | None = None


class TalentverseReportListResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    pageInfo: TalentversePageInfo
```

Use `dict` for report bodies because the payload is already schema-validated before publishing and contains nested SEO/GEO fields.

- [ ] **Step 6: Add read service**

Create `backend/app/services/talentverse_report_read_service.py`:

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TalentverseReport

PUBLISHED_STATUS = "published"
MAX_LIMIT = 100


class TalentverseCursorError(ValueError):
    pass


def list_published_talentverse_reports(
    db: Session,
    *,
    region: str | None = None,
    locale: str | None = None,
    status: str = PUBLISHED_STATUS,
    limit: int = 20,
    cursor: str | None = None,
    updated_after: datetime | None = None,
) -> dict:
    if status != PUBLISHED_STATUS:
        return {"items": [], "pageInfo": {"limit": _normalize_limit(limit), "nextCursor": None}}
    normalized_limit = _normalize_limit(limit)
    query = select(TalentverseReport).where(TalentverseReport.status == PUBLISHED_STATUS)
    if region:
        query = query.where(TalentverseReport.region == region)
    if locale:
        query = query.where(TalentverseReport.locale == locale)
    if updated_after is not None:
        query = query.where(TalentverseReport.updated_at > updated_after)
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        query = query.where(
            (TalentverseReport.updated_at < cursor_time)
            | ((TalentverseReport.updated_at == cursor_time) & (TalentverseReport.id < cursor_id))
        )
    rows = (
        db.execute(
            query.order_by(TalentverseReport.updated_at.desc(), TalentverseReport.id.desc()).limit(normalized_limit + 1)
        )
        .scalars()
        .all()
    )
    page_rows = rows[:normalized_limit]
    next_cursor = _encode_cursor(page_rows[-1]) if len(rows) > normalized_limit and page_rows else None
    return {
        "items": [_list_item(row) for row in page_rows],
        "pageInfo": {"limit": normalized_limit, "nextCursor": next_cursor},
    }


def get_published_talentverse_report_by_slug(db: Session, *, slug: str) -> dict | None:
    report = db.execute(
        select(TalentverseReport).where(TalentverseReport.slug == slug, TalentverseReport.status == PUBLISHED_STATUS)
    ).scalar_one_or_none()
    if report is None:
        return None
    return _detail_item(report)


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        return 20
    return min(limit, MAX_LIMIT)


def _list_item(report: TalentverseReport) -> dict:
    payload = dict(report.payload or {})
    return {
        "id": payload.get("id") or f"tv-report-{report.id}",
        "slug": report.slug,
        "region": report.region,
        "locale": report.locale,
        "title": payload.get("title") or report.title,
        "subtitle": payload.get("subtitle"),
        "executiveSummary": payload.get("executiveSummary"),
        "keySignals": list(payload.get("keySignals") or [])[:3],
        "methodologyNote": _methodology_summary(payload.get("methodologyNote")),
        "source": payload.get("source"),
        "seo": payload.get("seo"),
        "publishedAt": _iso(report.published_at),
        "updatedAt": _iso(report.updated_at),
        "version": report.version,
        "category": payload.get("category"),
        "tags": payload.get("tags") or [],
    }


def _detail_item(report: TalentverseReport) -> dict:
    payload = dict(report.payload or {})
    payload["id"] = payload.get("id") or f"tv-report-{report.id}"
    payload["slug"] = report.slug
    payload["region"] = report.region
    payload["locale"] = report.locale
    payload["status"] = report.status
    payload["publishedAt"] = payload.get("publishedAt") or _iso(report.published_at)
    payload["updatedAt"] = payload.get("updatedAt") or _iso(report.updated_at)
    payload["version"] = payload.get("version") or report.version
    return payload


def _methodology_summary(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {"sampleCount": value.get("sampleCount"), "windowDays": value.get("windowDays")}


def _iso(value: datetime | None) -> str | None:
    return value.replace(microsecond=0).isoformat() if value is not None else None


def _encode_cursor(report: TalentverseReport) -> str:
    return f"{report.updated_at.isoformat()}::{report.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        timestamp, id_text = cursor.split("::", 1)
        return datetime.fromisoformat(timestamp), int(id_text)
    except (ValueError, TypeError) as exc:
        raise TalentverseCursorError("Invalid cursor") from exc
```

- [ ] **Step 7: Add API router**

Create `backend/app/api/talentverse_reports.py`:

```python
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.talentverse_auth import require_reports_api_token
from app.db.database import get_db
from app.schemas.talentverse_report import TalentverseReportListResponse
from app.services.talentverse_report_read_service import (
    TalentverseCursorError,
    get_published_talentverse_report_by_slug,
    list_published_talentverse_reports,
)

router = APIRouter(
    prefix="/talentverse/reports",
    tags=["talentverse-reports"],
    dependencies=[Depends(require_reports_api_token)],
)


@router.get("", response_model=TalentverseReportListResponse)
def list_reports(
    region: Literal["global", "japan"] | None = Query(default=None),
    locale: Literal["zh-CN", "ja-JP"] | None = Query(default=None),
    status: Literal["published"] = Query(default="published"),
    limit: int = Query(default=20),
    cursor: str | None = Query(default=None),
    updatedAfter: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        return list_published_talentverse_reports(
            db,
            region=region,
            locale=locale,
            status=status,
            limit=limit,
            cursor=cursor,
            updated_after=updatedAfter,
        )
    except TalentverseCursorError as exc:
        raise HTTPException(status_code=422, detail="Invalid cursor") from exc


@router.get("/{slug}")
def get_report(slug: str, db: Session = Depends(get_db)):
    report = get_published_talentverse_report_by_slug(db, slug=slug)
    if report is None:
        raise HTTPException(status_code=404, detail="Talentverse report not found")
    return report
```

Modify `backend/app/main.py`:

```python
from app.api import claims, company_clue, crawl, health, home, talentverse_reports
```

```python
app.include_router(talentverse_reports.router, prefix="/api/v1")
```

- [ ] **Step 8: Run API tests**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_api.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit API task**

Run:

```bash
git add backend/app/core/config.py backend/.env.example backend/app/api/talentverse_auth.py backend/app/schemas/talentverse_report.py backend/app/services/talentverse_report_read_service.py backend/app/api/talentverse_reports.py backend/app/main.py backend/tests/test_talentverse_report_api.py
git commit -m "feat: expose authenticated talentverse report api"
```

---

## Task 5: Verification and Regression Safety

**Files:**
- No new files.

- [ ] **Step 1: Run focused Talentverse test suite**

Run:

```bash
cd backend
pytest tests/test_talentverse_report_model.py tests/test_talentverse_report_generation.py tests/test_talentverse_report_api.py tests/test_market_intelligence_living_refresh.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run home API regression tests**

Run:

```bash
cd backend
pytest tests/test_home_api.py tests/test_japan_home_feed.py tests/test_market_intelligence_home_read.py -q
```

Expected: all tests pass. This confirms `/api/v1/home` and `/api/v1/home/japan` behavior was not broken.

- [ ] **Step 3: Run full backend test suite**

Run:

```bash
cd backend
pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 4: Manual local API smoke test**

Set a local token for the running backend:

```powershell
$env:REPORTS_API_TOKEN="local-test-token"
```

Start API:

```powershell
cd backend
uvicorn app.main:app --reload
```

In another shell:

```bash
curl -i http://127.0.0.1:8000/api/v1/talentverse/reports
```

Expected: `401 Missing bearer token`.

Then:

```bash
curl -i http://127.0.0.1:8000/api/v1/talentverse/reports -H "Authorization: Bearer local-test-token"
```

Expected: `200 OK` with an `items` array. The array may be empty before a local report is generated.

- [ ] **Step 5: Commit verification notes if code changed during fixes**

If verification required code changes, commit them:

```bash
git add backend
git commit -m "test: verify talentverse report integration"
```

If verification required no code changes, do not create an empty commit.

---

## Deployment Notes

### Server Environment

Set on Tencent Cloud backend server:

```bash
cd /opt/bounty-pool/app/backend
printf '\nREPORTS_API_TOKEN=<set-a-long-random-token-here>\n' >> .env
sudo systemctl restart bounty-pool
```

Do not paste the real token into git, docs, screenshots, or chat logs.

### Post-Deploy Smoke

```bash
curl -i https://api.talentsignal.cloud/api/v1/talentverse/reports
```

Expected: `401`.

```bash
curl -i https://api.talentsignal.cloud/api/v1/talentverse/reports \
  -H "Authorization: Bearer <REPORTS_API_TOKEN>"
```

Expected: `200`.

### Backfill First Published Talentverse Report

After deploy, generate or backfill the latest global raw report variant with a one-off Python command:

```bash
cd /opt/bounty-pool/app/backend
/opt/bounty-pool/venv/bin/python3 - <<'PY'
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import MarketIntelligenceSnapshot
from app.services.region import GLOBAL_REGION
from app.services.talentverse_report_generation import generate_talentverse_report_for_snapshot

with SessionLocal() as db:
    snapshot = (
        db.execute(
            select(MarketIntelligenceSnapshot)
            .where(MarketIntelligenceSnapshot.region == GLOBAL_REGION)
            .where(MarketIntelligenceSnapshot.status == "success")
            .order_by(MarketIntelligenceSnapshot.generated_at.desc(), MarketIntelligenceSnapshot.id.desc())
        )
        .scalars()
        .first()
    )
    if snapshot is None:
        print({"status": "skipped", "reason": "no_success_global_snapshot"})
    else:
        print(generate_talentverse_report_for_snapshot(db, raw_snapshot_id=snapshot.id))
PY
```

Expected: `{"status": "published", ...}` or `{"status": "failed", ...}` with a sanitized error.

---

## Review Checklist

- Existing `/api/v1/home` remains unchanged.
- Existing `/api/v1/home/japan` remains unchanged.
- Japan raw report can still generate, but Talentverse variant generation is skipped.
- `failed` Talentverse reports are persisted but not returned by API.
- `published` API requires `Authorization: Bearer <REPORTS_API_TOKEN>`.
- Public API does not expose `canonical_url`, `source_name`, `full_description`, raw job URLs, or full JD.
- LLM output must contain FAQ, glossary terms, evidence refs, and SEO fields before publishing.
- No new external dependency is required.
- No frontend changes are required.
