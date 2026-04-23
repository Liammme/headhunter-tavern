# Estimated Bounty Write Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a low-coupling recruiter bounty estimation write path that computes and persists `estimated_bounty_amount` / `estimated_bounty_label` into `jobs.signal_tags`, keeps the existing home payload contract unchanged, and backfills existing rows without a schema migration.

**Architecture:** Keep bounty estimation in the write-path analysis layer as a pure rule engine. `job_enrichment` should call a dedicated estimator service and persist the result into `signal_tags`; `home_feed_aggregation` should remain read-only and only consume persisted estimate fields. Existing jobs should be updated by a separate backfill service and thin CLI entrypoint so the feature is visible immediately without waiting for the next crawl.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy ORM, pytest, existing `signal_tags` JSON persistence on `Job`

---

## File Structure

### Create

- `backend/app/services/bounty_estimation.py`
  - Pure rule engine for recruiter bounty estimation.
  - Owns salary-band assumptions, fee-rate rules, label formatting, and rule-version metadata.
- `backend/app/services/bounty_backfill_service.py`
  - Recomputes bounty estimates for existing `jobs` rows and writes them into `signal_tags`.
- `backend/app/cli/backfill_estimated_bounty.py`
  - Thin operational entrypoint that calls the backfill service and prints a JSON summary.
- `backend/tests/test_bounty_estimation.py`
  - Locks down the pure estimation rules.
- `backend/tests/test_bounty_backfill_service.py`
  - Verifies existing rows are updated without touching unrelated signal tags.

### Modify

- `backend/app/services/job_enrichment.py`
  - Calls the estimator during write-path enrichment and writes bounty fields into `signal_tags`.
- `backend/tests/test_job_enrichment.py`
  - Verifies new jobs carry estimated bounty signal tags after enrichment.
- `backend/tests/test_home_feed_aggregation.py`
  - Verifies the read path keeps using persisted estimate fields and only falls back to `"待估算"` when the write path truly left them empty.
- `backend/tests/test_home_api.py`
  - Verifies `/api/v1/home` still returns the same contract while exposing computed estimate values through existing fields.

### Do Not Modify

- `backend/app/services/home_feed.py`
  - Keep home query orchestration read-only.
- `backend/app/api/home.py`
  - Do not move business logic into the API layer.
- `backend/app/services/home_feed_aggregation.py`
  - Only read persisted bounty values here; do not add estimation rules here.
- `frontend/components/CompanyClaimSeal.tsx`
  - Existing UI already consumes `estimated_bounty_amount` / `estimated_bounty_label`; no frontend behavior change is required for the first pass.

## Domain Rule

The bounty estimate should model the recruiter's expected BD upside as a one-time fee equal to **10% to 20%** of the role's estimated annual cash compensation.

### Rule Version

- `bounty-rule-v1`

### Salary-Band Assumptions

Use annual RMB salary bands, not monthly salary. Keep the table explicit inside `bounty_estimation.py`.

```python
DEFAULT_ANNUAL_SALARY_BANDS = {
    "AI/算法": {
        "none": (240_000, 360_000),
        "senior": (360_000, 520_000),
        "staff": (500_000, 720_000),
        "principal": (600_000, 900_000),
        "lead": (480_000, 680_000),
        "architect": (550_000, 820_000),
        "director": (700_000, 1_100_000),
        "head": (780_000, 1_200_000),
        "vp": (900_000, 1_500_000),
        "founding": (650_000, 1_000_000),
    },
    "技术": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (460_000, 680_000),
        "principal": (560_000, 820_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (650_000, 980_000),
        "head": (720_000, 1_080_000),
        "vp": (850_000, 1_350_000),
        "founding": (600_000, 900_000),
    },
    "数据": {
        "none": (200_000, 300_000),
        "senior": (300_000, 420_000),
        "staff": (420_000, 600_000),
        "principal": (520_000, 760_000),
        "lead": (400_000, 560_000),
        "architect": (460_000, 680_000),
        "director": (600_000, 900_000),
        "head": (680_000, 1_000_000),
        "vp": (780_000, 1_200_000),
        "founding": (560_000, 820_000),
    },
    "产品": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (420_000, 620_000),
        "principal": (500_000, 760_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (620_000, 920_000),
        "head": (700_000, 1_000_000),
        "vp": (820_000, 1_260_000),
        "founding": (560_000, 820_000),
    },
    "增长": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "商务": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "运营": {
        "none": (160_000, 240_000),
        "senior": (220_000, 320_000),
        "staff": (280_000, 400_000),
        "principal": (320_000, 460_000),
        "lead": (300_000, 440_000),
        "architect": (320_000, 460_000),
        "director": (420_000, 620_000),
        "head": (500_000, 720_000),
        "vp": (620_000, 920_000),
        "founding": (360_000, 520_000),
    },
}
```

### Fee-Rate Assumptions

Start from `12%` and clamp to `10%`–`20%`.

```python
def _resolve_fee_rate_pct(input: BountyEstimateInput) -> int:
    rate = 12
    if input.hard_to_fill:
        rate += 3
    if input.critical:
        rate += 2
    if input.role_complexity == "high":
        rate += 1
    if input.business_criticality == "high":
        rate += 1
    if input.urgent:
        rate += 1
    if "long_running" in input.time_pressure_signals:
        rate += 1
    if input.company_signal == "hot":
        rate += 1
    return max(10, min(rate, 20))
```

### Persisted Signal Keys

Persist all of these into `Job.signal_tags`:

```python
{
    "estimated_bounty_amount": 150000,
    "estimated_bounty_label": "¥120,000-¥180,000",
    "estimated_bounty_min": 120000,
    "estimated_bounty_max": 180000,
    "estimated_bounty_rate_pct": 20,
    "estimated_bounty_rule_version": "bounty-rule-v1",
    "estimated_bounty_confidence": "medium",
}
```

Do **not** add a database column. Keep this inside `signal_tags` to avoid a schema migration.

---

### Task 1: Add Pure Bounty Estimation Rules

**Files:**
- Create: `backend/app/services/bounty_estimation.py`
- Test: `backend/tests/test_bounty_estimation.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.bounty_estimation import BountyEstimateInput, estimate_bounty


def test_estimate_bounty_returns_high_end_range_for_ai_principal():
    estimate = estimate_bounty(
        BountyEstimateInput(
            category="AI/算法",
            seniority="principal",
            domain_tag="AI",
            urgent=True,
            critical=True,
            hard_to_fill=True,
            role_complexity="high",
            business_criticality="high",
            compensation_signal="unknown",
            company_signal="hot",
            time_pressure_signals=("urgent", "long_running"),
        )
    )

    assert estimate.amount == 150000
    assert estimate.min_amount == 120000
    assert estimate.max_amount == 180000
    assert estimate.rate_pct == 20
    assert estimate.label == "¥120,000-¥180,000"
    assert estimate.rule_version == "bounty-rule-v1"


def test_estimate_bounty_keeps_low_complexity_ops_roles_near_floor():
    estimate = estimate_bounty(
        BountyEstimateInput(
            category="运营",
            seniority="none",
            domain_tag="工具/SaaS",
            urgent=False,
            critical=False,
            hard_to_fill=False,
            role_complexity="low",
            business_criticality="low",
            compensation_signal="unknown",
            company_signal="neutral",
            time_pressure_signals=(),
        )
    )

    assert estimate.amount == 24000
    assert estimate.min_amount == 19200
    assert estimate.max_amount == 28800
    assert estimate.rate_pct == 12
    assert estimate.label == "¥19,200-¥28,800"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_bounty_estimation.py -q`
Expected: FAIL with `ModuleNotFoundError` or import error for `app.services.bounty_estimation`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


BountyEstimateRuleVersion = "bounty-rule-v1"


@dataclass(frozen=True)
class BountyEstimateInput:
    category: str
    seniority: str
    domain_tag: str
    urgent: bool
    critical: bool
    hard_to_fill: bool
    role_complexity: str
    business_criticality: str
    compensation_signal: str
    company_signal: str
    time_pressure_signals: tuple[str, ...]


@dataclass(frozen=True)
class BountyEstimate:
    amount: int
    min_amount: int
    max_amount: int
    rate_pct: int
    label: str
    confidence: str
    rule_version: str


DEFAULT_ANNUAL_SALARY_BANDS = {
    "AI/算法": {"principal": (600_000, 900_000), "none": (240_000, 360_000)},
    "运营": {"none": (160_000, 240_000)},
}


def estimate_bounty(input: BountyEstimateInput) -> BountyEstimate:
    annual_min, annual_max = _resolve_salary_band(input.category, input.seniority)
    rate_pct = _resolve_fee_rate_pct(input)
    min_amount = int(annual_min * rate_pct / 100)
    max_amount = int(annual_max * rate_pct / 100)
    amount = int(round(((min_amount + max_amount) / 2) / 1000) * 1000)
    label = f"¥{min_amount:,.0f}-¥{max_amount:,.0f}"
    confidence = "high" if input.compensation_signal == "strong" else "medium"
    return BountyEstimate(
        amount=amount,
        min_amount=min_amount,
        max_amount=max_amount,
        rate_pct=rate_pct,
        label=label,
        confidence=confidence,
        rule_version=BountyEstimateRuleVersion,
    )


def _resolve_salary_band(category: str, seniority: str) -> tuple[int, int]:
    category_bands = DEFAULT_ANNUAL_SALARY_BANDS.get(category) or DEFAULT_ANNUAL_SALARY_BANDS["运营"]
    return category_bands.get(seniority) or category_bands["none"]


def _resolve_fee_rate_pct(input: BountyEstimateInput) -> int:
    rate = 12
    if input.hard_to_fill:
        rate += 3
    if input.critical:
        rate += 2
    if input.role_complexity == "high":
        rate += 1
    if input.business_criticality == "high":
        rate += 1
    if input.urgent:
        rate += 1
    if "long_running" in input.time_pressure_signals:
        rate += 1
    if input.company_signal == "hot":
        rate += 1
    return max(10, min(rate, 20))
```

- [ ] **Step 4: Expand implementation to the full salary-band table**

```python
DEFAULT_ANNUAL_SALARY_BANDS = {
    "AI/算法": {
        "none": (240_000, 360_000),
        "senior": (360_000, 520_000),
        "staff": (500_000, 720_000),
        "principal": (600_000, 900_000),
        "lead": (480_000, 680_000),
        "architect": (550_000, 820_000),
        "director": (700_000, 1_100_000),
        "head": (780_000, 1_200_000),
        "vp": (900_000, 1_500_000),
        "founding": (650_000, 1_000_000),
    },
    "技术": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (460_000, 680_000),
        "principal": (560_000, 820_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (650_000, 980_000),
        "head": (720_000, 1_080_000),
        "vp": (850_000, 1_350_000),
        "founding": (600_000, 900_000),
    },
    "数据": {
        "none": (200_000, 300_000),
        "senior": (300_000, 420_000),
        "staff": (420_000, 600_000),
        "principal": (520_000, 760_000),
        "lead": (400_000, 560_000),
        "architect": (460_000, 680_000),
        "director": (600_000, 900_000),
        "head": (680_000, 1_000_000),
        "vp": (780_000, 1_200_000),
        "founding": (560_000, 820_000),
    },
    "产品": {
        "none": (220_000, 320_000),
        "senior": (320_000, 460_000),
        "staff": (420_000, 620_000),
        "principal": (500_000, 760_000),
        "lead": (420_000, 620_000),
        "architect": (500_000, 760_000),
        "director": (620_000, 920_000),
        "head": (700_000, 1_000_000),
        "vp": (820_000, 1_260_000),
        "founding": (560_000, 820_000),
    },
    "增长": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "商务": {
        "none": (180_000, 260_000),
        "senior": (260_000, 380_000),
        "staff": (320_000, 480_000),
        "principal": (380_000, 560_000),
        "lead": (340_000, 500_000),
        "architect": (380_000, 560_000),
        "director": (480_000, 720_000),
        "head": (560_000, 820_000),
        "vp": (680_000, 1_000_000),
        "founding": (420_000, 620_000),
    },
    "运营": {
        "none": (160_000, 240_000),
        "senior": (220_000, 320_000),
        "staff": (280_000, 400_000),
        "principal": (320_000, 460_000),
        "lead": (300_000, 440_000),
        "architect": (320_000, 460_000),
        "director": (420_000, 620_000),
        "head": (500_000, 720_000),
        "vp": (620_000, 920_000),
        "founding": (360_000, 520_000),
    },
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_bounty_estimation.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/bounty_estimation.py backend/tests/test_bounty_estimation.py
git commit -m "feat: add pure estimated bounty rules"
```

### Task 2: Wire Estimates into Job Enrichment

**Files:**
- Modify: `backend/app/services/job_enrichment.py`
- Test: `backend/tests/test_job_enrichment.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_job_payload_adds_estimated_bounty_signal_tags():
    job = NormalizedJob(
        source_job_id="founding-ai",
        canonical_url="https://open-gradient.ai/careers/principal-ai-engineer",
        title="Principal AI Engineer",
        company="Open Gradient",
        location="Remote",
        remote_type="remote",
        employment_type="full-time",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime.now().replace(microsecond=0),
        raw_payload={"site": "demo-board"},
    )

    payload = build_job_payload(job)

    assert payload["signal_tags"]["estimated_bounty_amount"] == 150000
    assert payload["signal_tags"]["estimated_bounty_label"] == "¥120,000-¥180,000"
    assert payload["signal_tags"]["estimated_bounty_rate_pct"] == 20
    assert payload["signal_tags"]["estimated_bounty_rule_version"] == "bounty-rule-v1"
    assert payload["signal_tags"]["estimated_bounty_confidence"] == "medium"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_job_enrichment.py::test_build_job_payload_adds_estimated_bounty_signal_tags -q`
Expected: FAIL because `estimated_bounty_amount` is missing from `signal_tags`

- [ ] **Step 3: Write minimal implementation**

```python
from app.services.bounty_estimation import BountyEstimateInput, estimate_bounty


def _build_bounty_estimate_input(facts: JobFacts) -> BountyEstimateInput:
    return BountyEstimateInput(
        category=facts.category,
        seniority=facts.seniority,
        domain_tag=facts.domain_tag,
        urgent=facts.urgent,
        critical=facts.critical,
        hard_to_fill=facts.hard_to_fill,
        role_complexity=facts.role_complexity,
        business_criticality=facts.business_criticality,
        compensation_signal=facts.compensation_signal,
        company_signal=facts.company_signal,
        time_pressure_signals=facts.time_pressure_signals,
    )


def enrich_job(job: NormalizedJob) -> JobEnrichmentResult:
    standardized = standardize_job_input(job)
    facts = extract_job_facts(standardized, now=standardized.collected_at)
    signal_tags = build_legacy_signal_tags(facts)

    bounty_estimate = estimate_bounty(_build_bounty_estimate_input(facts))
    signal_tags.update(
        {
            "estimated_bounty_amount": bounty_estimate.amount,
            "estimated_bounty_label": bounty_estimate.label,
            "estimated_bounty_min": bounty_estimate.min_amount,
            "estimated_bounty_max": bounty_estimate.max_amount,
            "estimated_bounty_rate_pct": bounty_estimate.rate_pct,
            "estimated_bounty_rule_version": bounty_estimate.rule_version,
            "estimated_bounty_confidence": bounty_estimate.confidence,
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_job_enrichment.py::test_build_job_payload_adds_estimated_bounty_signal_tags -q`
Expected: PASS

- [ ] **Step 5: Run the focused write-path suite**

Run: `pytest backend/tests/test_bounty_estimation.py backend/tests/test_job_enrichment.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/job_enrichment.py backend/tests/test_job_enrichment.py
git commit -m "feat: persist estimated bounty in enrichment"
```

### Task 3: Backfill Existing Jobs Without Schema Changes

**Files:**
- Create: `backend/app/services/bounty_backfill_service.py`
- Create: `backend/app/cli/backfill_estimated_bounty.py`
- Test: `backend/tests/test_bounty_backfill_service.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime

from app.models import Job
from app.services.bounty_backfill_service import backfill_estimated_bounties


def test_backfill_estimated_bounties_updates_jobs_missing_estimates(db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/1",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 23, 9, 0, 0),
        collected_at=datetime(2026, 4, 23, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={"display_tags": ["AI", "Senior", "核心岗位"]},
    )
    db_session.add(job)
    db_session.commit()

    summary = backfill_estimated_bounties(db_session)
    refreshed = db_session.get(Job, job.id)

    assert summary == {"scanned_jobs": 1, "updated_jobs": 1, "skipped_jobs": 0}
    assert refreshed.signal_tags["estimated_bounty_amount"] == 150000
    assert refreshed.signal_tags["estimated_bounty_label"] == "¥120,000-¥180,000"
    assert refreshed.signal_tags["display_tags"] == ["AI", "Senior", "核心岗位"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_bounty_backfill_service.py -q`
Expected: FAIL with import error for `app.services.bounty_backfill_service`

- [ ] **Step 3: Write minimal implementation**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.bounty_estimation import BountyEstimateInput, estimate_bounty
from app.services.job_facts import StandardizedJobInput, extract_job_facts


def backfill_estimated_bounties(db: Session) -> dict:
    jobs = db.execute(select(Job).order_by(Job.id.asc())).scalars().all()
    updated_jobs = 0
    skipped_jobs = 0

    for job in jobs:
        signal_tags = dict(job.signal_tags or {})
        if isinstance(signal_tags.get("estimated_bounty_amount"), int) and isinstance(signal_tags.get("estimated_bounty_label"), str):
            skipped_jobs += 1
            continue

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
        estimate = estimate_bounty(
            BountyEstimateInput(
                category=facts.category,
                seniority=facts.seniority,
                domain_tag=facts.domain_tag,
                urgent=facts.urgent,
                critical=facts.critical,
                hard_to_fill=facts.hard_to_fill,
                role_complexity=facts.role_complexity,
                business_criticality=facts.business_criticality,
                compensation_signal=facts.compensation_signal,
                company_signal=facts.company_signal,
                time_pressure_signals=facts.time_pressure_signals,
            )
        )

        signal_tags.update(
            {
                "estimated_bounty_amount": estimate.amount,
                "estimated_bounty_label": estimate.label,
                "estimated_bounty_min": estimate.min_amount,
                "estimated_bounty_max": estimate.max_amount,
                "estimated_bounty_rate_pct": estimate.rate_pct,
                "estimated_bounty_rule_version": estimate.rule_version,
                "estimated_bounty_confidence": estimate.confidence,
            }
        )
        job.signal_tags = signal_tags
        updated_jobs += 1

    db.commit()
    return {"scanned_jobs": len(jobs), "updated_jobs": updated_jobs, "skipped_jobs": skipped_jobs}
```

- [ ] **Step 4: Add the thin CLI wrapper**

```python
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.bounty_backfill_service import backfill_estimated_bounties


def main() -> None:
    init_db()
    with SessionLocal() as db:
        summary = backfill_estimated_bounties(db)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests and the CLI smoke check**

Run: `pytest backend/tests/test_bounty_backfill_service.py -q`
Expected: PASS

Run: `python -m app.cli.backfill_estimated_bounty`
Expected: JSON summary like `{"scanned_jobs": 418, "updated_jobs": 418, "skipped_jobs": 0}`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/bounty_backfill_service.py backend/app/cli/backfill_estimated_bounty.py backend/tests/test_bounty_backfill_service.py
git commit -m "feat: add estimated bounty backfill path"
```

### Task 4: Lock the Read Path to Persisted Estimates

**Files:**
- Modify: `backend/tests/test_home_feed_aggregation.py`
- Modify: `backend/tests/test_home_api.py`

- [ ] **Step 1: Add a read-path test at the aggregation layer**

```python
def test_build_day_payloads_keeps_persisted_estimated_bounty_values():
    jobs = [
        build_job(
            job_id=1,
            company="OpenGradient",
            company_normalized="opengradient",
            title="Staff AI Engineer",
            bounty_grade="high",
            days_ago=0,
        )
    ]
    jobs[0].signal_tags.update(
        {
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
        }
    )

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount == 150000
    assert company.estimated_bounty_label == "¥120,000-¥180,000"
```

- [ ] **Step 2: Add an API contract test using the real home builder**

```python
def test_home_payload_exposes_estimated_bounty_from_persisted_signal_tags(client, db_session):
    job = Job(
        canonical_url="https://jobs.example.com/opengradient/principal-ai-engineer",
        source_name="demo-board",
        title="Principal AI Engineer",
        company="OpenGradient",
        company_normalized="opengradient",
        description="Build LLM platform and hiring roadmap.",
        posted_at=datetime(2026, 4, 18, 9, 0, 0),
        collected_at=datetime(2026, 4, 18, 9, 0, 0),
        bounty_grade="medium",
        signal_tags={
            "display_tags": ["AI", "Senior", "核心岗位"],
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
        },
    )
    db_session.add(job)
    db_session.commit()

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    company = response.json()["days"][0]["companies"][0]
    assert company["estimated_bounty_amount"] == 150000
    assert company["estimated_bounty_label"] == "¥120,000-¥180,000"
```

- [ ] **Step 3: Run the focused read-path suite**

Run: `pytest backend/tests/test_home_feed_aggregation.py backend/tests/test_home_api.py -q`
Expected: PASS

- [ ] **Step 4: Run the full minimal regression bundle**

Run: `pytest backend/tests/test_bounty_estimation.py backend/tests/test_job_enrichment.py backend/tests/test_bounty_backfill_service.py backend/tests/test_home_feed_aggregation.py backend/tests/test_home_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_home_feed_aggregation.py backend/tests/test_home_api.py
git commit -m "test: lock estimated bounty write path contract"
```

### Task 5: Backfill the Branch Database and Verify End-to-End

**Files:**
- Modify: none
- Run: `backend/bounty_pool.db`

- [ ] **Step 1: Run the backfill against the local branch database**

Run: `cd backend && python -m app.cli.backfill_estimated_bounty`
Expected: JSON summary with `updated_jobs > 0` on the first run

- [ ] **Step 2: Start the local backend**

Run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
Expected: startup succeeds with no import errors

- [ ] **Step 3: Verify the home payload now includes estimate values**

Run:

```bash
python - <<'PY'
import requests
payload = requests.get("http://127.0.0.1:8000/api/v1/home", timeout=10).json()
company = payload["days"][0]["companies"][0]
print(company["company"])
print(company["estimated_bounty_amount"])
print(company["estimated_bounty_label"])
PY
```

Expected: first company prints a non-null amount and a label like `¥120,000-¥180,000`

- [ ] **Step 4: Verify idempotency**

Run: `cd backend && python -m app.cli.backfill_estimated_bounty`
Expected: JSON summary with `updated_jobs = 0` and `skipped_jobs` equal to the number of already-estimated rows

- [ ] **Step 5: Final commit**

```bash
git add backend/app/services/bounty_estimation.py backend/app/services/bounty_backfill_service.py backend/app/cli/backfill_estimated_bounty.py backend/app/services/job_enrichment.py backend/tests/test_bounty_estimation.py backend/tests/test_bounty_backfill_service.py backend/tests/test_job_enrichment.py backend/tests/test_home_feed_aggregation.py backend/tests/test_home_api.py
git commit -m "feat: add estimated bounty write path"
```

## Self-Review

### Spec Coverage

- Estimate rule defined: yes, via salary-band + fee-rate table inside `bounty_estimation.py`
- Low-coupling write path: yes, estimator stays pure and only `job_enrichment` writes
- Existing rows updated: yes, via dedicated backfill service + CLI
- Existing API contract preserved: yes, existing `estimated_bounty_amount` / `estimated_bounty_label` fields remain unchanged

### Placeholder Scan

- No `TODO`, `TBD`, or “implement later”
- Every code step contains concrete code
- Every verification step contains a concrete command and expected result

### Type Consistency

- `estimated_bounty_amount` stays `int | None`
- `estimated_bounty_label` stays `str | None`
- Rule metadata remains inside `signal_tags`, avoiding schema drift

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-estimated-bounty-write-path.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
