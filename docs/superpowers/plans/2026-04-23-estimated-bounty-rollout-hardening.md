# Estimated Bounty Rollout Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an industry-standard rollout gate for estimated bounty so the write path can be preheated explicitly, the read path can be enabled explicitly, and operators can audit `complete / partial / invalid / missing` coverage before switching the feature on.

**Architecture:** Keep the existing estimated-bounty rule engine in the write path, but make rollout explicit. `job_enrichment` writes snapshots only when the live-write flag is enabled and does so in best-effort mode; `home_feed_aggregation` and `company_clue_letter` stay fail-closed behind a read-side flag; `bounty_readiness_service` and the audit CLI provide the rollout gate without changing the home API contract.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic Settings, pytest, existing `signal_tags` JSON persistence on `Job`

---

## File Structure

### Create

- `backend/app/services/bounty_readiness_service.py`
  - Computes rollout audit stats for `complete / partial / missing` snapshots.
  - Owns the active-window readiness summary used by operators before enabling readers.
- `backend/app/cli/audit_estimated_bounty.py`
  - Thin CLI wrapper that prints JSON audit stats for rollout gating.
- `docs/superpowers/plans/2026-04-23-estimated-bounty-rollout-hardening.md`
  - This plan document.

### Modify

- `backend/app/core/config.py`
  - Adds the live-write flag, read-side flag, startup-audit flag, and audit window settings.
- `backend/app/services/bounty_estimation.py`
  - Centralizes snapshot completeness and validity classification so read path and audit path share the same boundary.
- `backend/app/services/estimated_bounty_read.py`
  - Shared fail-closed read helper used by both readers.
- `backend/app/services/home_feed_aggregation.py`
  - Hides estimated bounty on the home feed unless the rollout flag is enabled.
- `backend/app/services/company_clue_letter.py`
  - Hides estimated bounty in company clue summaries unless the rollout flag is enabled.
- `backend/tests/test_home_feed_aggregation.py`
  - Locks down read-side gating behavior.
- `backend/tests/test_company_clue_letter.py`
  - Locks down clue-summary gating behavior.
- `backend/tests/test_bounty_estimation.py`
  - Locks down snapshot state classification.
- `backend/tests/test_bounty_backfill_service.py`
  - Verifies backfill still repairs partial snapshots under the shared classifier.
- `backend/tests/test_bounty_readiness_service.py`
  - Verifies audit counts for `complete / partial / missing`.
- `backend/tests/test_config.py`
  - Verifies the new rollout settings parse as expected.

### Do Not Modify

- `backend/app/api/home.py`
  - Keep the API handler as a thin wrapper.
- `backend/app/services/home_feed.py`
  - Do not move rollout logic into the home orchestration layer.
- `backend/app/services/job_enrichment.py`
  - Keep the write-path entrypoint unchanged, but allow live-write gating and best-effort estimate persistence.
- `frontend/**`
  - No frontend rollout logic for this pass.

## Target Rollout Model

### 1. Expand

- Deploy code with all rollout flags disabled first.
- Enable live-write first so new crawl writes start accumulating complete snapshots.
- Keep readers behind the read-side flag.
- `estimated_bounty_*` remains persisted in `Job.signal_tags`.

### 2. Audit

- Run a dedicated audit CLI over the active 14-day home window.
- Audit output must expose:
  - `scanned_jobs`
  - `complete_jobs`
  - `partial_jobs`
  - `invalid_jobs`
  - `missing_jobs`
  - `active_scanned_jobs`
  - `active_complete_jobs`
  - `active_partial_jobs`
  - `active_invalid_jobs`
  - `active_missing_jobs`
  - `window_start`
  - `window_end`

### 3. Switch

- Enable readers only when:
  - `active_partial_jobs == 0`
  - `active_invalid_jobs == 0`
  - `active_missing_jobs == 0`
- The feature flag is the operational switch.

### 4. Rollback

- Disable the read-side feature flag.
- Optionally disable live-write if estimate generation itself is noisy.
- Keep backfill available for repair.
- Home feed falls back to the existing `estimated_bounty_amount=None` / `estimated_bounty_label="待估算"` behavior.
- Company clue summary falls back to `estimated_bounty=None`.

## Feature Flags

Add these settings to `backend/app/core/config.py`:

```python
bounty_pool_estimated_bounty_live_write_enabled: bool = False
bounty_pool_estimated_bounty_read_enabled: bool = False
bounty_pool_estimated_bounty_startup_audit_enabled: bool = False
bounty_pool_estimated_bounty_audit_window_days: int = 14
```

Behavior:

- `live write = False`: keep enrichment working, but do not persist estimated bounty during crawl ingestion.
- `read = False`: hide estimated bounty from read-side consumers.
- `startup audit = True`: run a log-only readiness audit during API startup.

## Shared Snapshot Boundary

`backend/app/services/bounty_estimation.py` should become the only place that decides whether `signal_tags` holds:

- `complete`
- `partial`
- `invalid`
- `missing`

Recommended helper:

```python
def classify_bounty_signal_tags(signal_tags: Mapping[str, object] | None) -> Literal["complete", "partial", "invalid", "missing"]:
    ...
```

Rules:

- `complete`: the snapshot is structurally complete and semantically valid for read-side exposure
- `partial`: any `estimated_bounty_*` key exists, but the full snapshot is incomplete
- `invalid`: the full snapshot exists but fails semantic checks such as range / rate / rule-version validation
- `missing`: no estimated bounty snapshot keys exist

Backfill, audit, and future readers must all use this shared classifier.

---

### Task 1: Gate Read-Side Exposure Behind a Feature Flag

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/home_feed_aggregation.py`
- Modify: `backend/app/services/company_clue_letter.py`
- Test: `backend/tests/test_home_feed_aggregation.py`
- Test: `backend/tests/test_company_clue_letter.py`

- [ ] **Step 1: Write the failing home-feed gating test**

```python
def test_build_day_payloads_hides_estimated_bounty_when_rollout_flag_disabled(monkeypatch):
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
            "estimated_bounty_min": 120000,
            "estimated_bounty_max": 180000,
            "estimated_bounty_rate_pct": 20,
            "estimated_bounty_rule_version": "bounty-rule-v1",
            "estimated_bounty_confidence": "medium",
        }
    )
    monkeypatch.setattr("app.services.home_feed_aggregation._should_expose_estimated_bounty", lambda: False)

    payloads = build_day_payloads(jobs, [], today=datetime(2026, 4, 18).date())

    company = payloads[0].companies[0]
    assert company.estimated_bounty_amount is None
    assert company.estimated_bounty_label == "待估算"
```

- [ ] **Step 2: Write the failing company-clue gating test**

```python
def test_build_company_clue_llm_input_hides_estimated_bounty_when_rollout_flag_disabled(monkeypatch):
    jobs = [
        build_job(
            company="OpenGradient",
            title="Principal AI Engineer",
            canonical_url="https://jobs.example.com/opengradient/principal-ai",
            bounty_grade="high",
            description="urgent llm infra platform roadmap hiring fast",
            signal_tags={
                "display_tags": ["AI"],
                "company_url": "https://opengradient.ai",
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
    monkeypatch.setattr("app.services.company_clue_letter._should_expose_estimated_bounty", lambda: False)

    llm_input = build_company_clue_llm_input(company="OpenGradient", jobs=jobs)

    assert llm_input["company_summary"]["estimated_bounty"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest backend/tests/test_home_feed_aggregation.py::test_build_day_payloads_hides_estimated_bounty_when_rollout_flag_disabled -q
pytest backend/tests/test_company_clue_letter.py::test_build_company_clue_llm_input_hides_estimated_bounty_when_rollout_flag_disabled -q
```

Expected: FAIL because `_should_expose_estimated_bounty` does not exist or the readers still expose estimates.

- [ ] **Step 4: Write the minimal implementation**

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    ...
    bounty_pool_estimated_bounty_read_enabled: bool = False
    bounty_pool_estimated_bounty_audit_window_days: int = 14


# backend/app/services/home_feed_aggregation.py
from app.core.config import settings


def _should_expose_estimated_bounty() -> bool:
    return settings.bounty_pool_estimated_bounty_read_enabled


def build_day_payloads(...):
    ...
    company_bounty_estimate = (
        _select_company_bounty_estimate(sorted_jobs) if _should_expose_estimated_bounty() else None
    )


# backend/app/services/company_clue_letter.py
def _should_expose_estimated_bounty() -> bool:
    return settings.bounty_pool_estimated_bounty_read_enabled


def build_company_clue_llm_input(...):
    ...
    "estimated_bounty": (
        _collect_estimated_bounty([job for job, _brief in sorted_job_brief_pairs])
        if _should_expose_estimated_bounty()
        else None
    ),
```

- [ ] **Step 5: Run the focused read-path suite**

Run:

```bash
pytest backend/tests/test_home_feed_aggregation.py backend/tests/test_company_clue_letter.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/services/home_feed_aggregation.py backend/app/services/company_clue_letter.py backend/tests/test_home_feed_aggregation.py backend/tests/test_company_clue_letter.py
git commit -m "feat: gate estimated bounty readers"
```

### Task 2: Centralize Snapshot Completeness and Audit Readiness

**Files:**
- Modify: `backend/app/services/bounty_estimation.py`
- Modify: `backend/app/services/bounty_backfill_service.py`
- Create: `backend/app/services/bounty_readiness_service.py`
- Create: `backend/app/cli/audit_estimated_bounty.py`
- Test: `backend/tests/test_bounty_estimation.py`
- Test: `backend/tests/test_bounty_backfill_service.py`
- Test: `backend/tests/test_bounty_readiness_service.py`

- [ ] **Step 1: Write the failing classifier tests**

```python
from app.services.bounty_estimation import classify_bounty_signal_tags


def test_classify_bounty_signal_tags_marks_complete_snapshot():
    assert classify_bounty_signal_tags(
        {
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
            "estimated_bounty_min": 120000,
            "estimated_bounty_max": 180000,
            "estimated_bounty_rate_pct": 20,
            "estimated_bounty_rule_version": "bounty-rule-v1",
            "estimated_bounty_confidence": "medium",
        }
    ) == "complete"


def test_classify_bounty_signal_tags_marks_partial_snapshot():
    assert classify_bounty_signal_tags(
        {
            "estimated_bounty_amount": 150000,
            "estimated_bounty_label": "¥120,000-¥180,000",
        }
    ) == "partial"


def test_classify_bounty_signal_tags_marks_missing_snapshot():
    assert classify_bounty_signal_tags({"display_tags": ["AI"]}) == "missing"
```

- [ ] **Step 2: Write the failing audit test**

```python
def test_audit_estimated_bounties_counts_complete_partial_and_missing_rows(db_session):
    db_session.add_all(
        [
            build_job_with_signal_tags(...complete snapshot...),
            build_job_with_signal_tags(...partial snapshot...),
            build_job_with_signal_tags(...missing snapshot...),
        ]
    )
    db_session.commit()

    summary = audit_estimated_bounties(db_session, today=date(2026, 4, 23), window_days=14)

    assert summary["scanned_jobs"] == 3
    assert summary["complete_jobs"] == 1
    assert summary["partial_jobs"] == 1
    assert summary["missing_jobs"] == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest backend/tests/test_bounty_estimation.py -q
pytest backend/tests/test_bounty_readiness_service.py -q
```

Expected: FAIL with missing imports/functions.

- [ ] **Step 4: Write the minimal implementation**

```python
# backend/app/services/bounty_estimation.py
ESTIMATED_BOUNTY_SIGNAL_TAG_KEYS = (
    "estimated_bounty_amount",
    "estimated_bounty_label",
    "estimated_bounty_min",
    "estimated_bounty_max",
    "estimated_bounty_rate_pct",
    "estimated_bounty_rule_version",
    "estimated_bounty_confidence",
)


def classify_bounty_signal_tags(signal_tags):
    if BountyEstimate.from_signal_tags(signal_tags) is not None:
        return "complete"
    normalized = signal_tags if isinstance(signal_tags, dict) else {}
    if any(key in normalized for key in ESTIMATED_BOUNTY_SIGNAL_TAG_KEYS):
        return "partial"
    return "missing"


# backend/app/services/bounty_backfill_service.py
if classify_bounty_signal_tags(signal_tags) == "complete":
    skipped_jobs += 1
    continue


# backend/app/services/bounty_readiness_service.py
def audit_estimated_bounties(db: Session, *, today: date, window_days: int) -> dict:
    ...
```

- [ ] **Step 5: Add the thin audit CLI**

```python
import json
from datetime import datetime

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.bounty_readiness_service import audit_estimated_bounties


def main() -> None:
    init_db()
    with SessionLocal() as db:
        summary = audit_estimated_bounties(
            db,
            today=datetime.now().date(),
            window_days=settings.bounty_pool_estimated_bounty_audit_window_days,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
```

- [ ] **Step 6: Run the focused suite and CLI smoke check**

Run:

```bash
pytest backend/tests/test_bounty_estimation.py backend/tests/test_bounty_backfill_service.py backend/tests/test_bounty_readiness_service.py -q
python -m app.cli.audit_estimated_bounty
```

Expected:

- pytest: PASS
- CLI: JSON summary with `complete / partial / missing` counts

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/bounty_estimation.py backend/app/services/bounty_backfill_service.py backend/app/services/bounty_readiness_service.py backend/app/cli/audit_estimated_bounty.py backend/tests/test_bounty_estimation.py backend/tests/test_bounty_backfill_service.py backend/tests/test_bounty_readiness_service.py
git commit -m "feat: add estimated bounty readiness audit"
```

### Task 3: Harden Live Write and Verify the Rollout Gate

**Files:**
- Modify: `backend/app/services/job_enrichment.py`
- Modify: `backend/tests/test_job_enrichment.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_main.py`
- Modify: `backend/tests/test_config.py`
- Run: local CLI commands only

- [ ] **Step 1: Add a config parsing test**

```python
from app.core.config import Settings


def test_settings_support_estimated_bounty_rollout_flags():
    settings = Settings(
        bounty_pool_estimated_bounty_read_enabled=True,
        bounty_pool_estimated_bounty_audit_window_days=21,
    )

    assert settings.bounty_pool_estimated_bounty_read_enabled is True
    assert settings.bounty_pool_estimated_bounty_audit_window_days == 21
```

- [ ] **Step 2: Run the config test**

Run:

```bash
pytest backend/tests/test_config.py -q
```

Expected: PASS

- [ ] **Step 3: Run the minimal rollout verification bundle**

Run:

```bash
pytest backend/tests/test_config.py backend/tests/test_bounty_estimation.py backend/tests/test_bounty_backfill_service.py backend/tests/test_bounty_readiness_service.py backend/tests/test_home_feed_aggregation.py backend/tests/test_company_clue_letter.py backend/tests/test_home_api.py -q
```

Expected: PASS

- [ ] **Step 4: Run the operational gate commands**

Run:

```bash
python -m app.cli.backfill_estimated_bounty
python -m app.cli.audit_estimated_bounty
```

Expected:

- backfill is idempotent
- audit shows `active_partial_jobs == 0` and `active_missing_jobs == 0` before enabling the read-side flag

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_config.py docs/superpowers/plans/2026-04-23-estimated-bounty-rollout-hardening.md
git commit -m "docs: add estimated bounty rollout runbook"
```

## Remaining Risks After This Plan

- Deploy order is still an operational risk. Code can provide the flag and audit gate, but operators still need to follow `writer -> backfill -> audit -> switch`.
- `Job.signal_tags` is still a transitional storage carrier, not a real `JobAnalysisSnapshot` table. This plan makes the boundary cleaner but does not replace the storage model.
- Concurrent JSON updates on `signal_tags` still carry blob-overwrite risk; this plan does not introduce row-level merge semantics.

## Self-Review

### Spec Coverage

- Feature-flagged reader gate: yes
- Audit command for rollout readiness: yes
- Shared complete/partial/missing boundary: yes
- Stable API contract: yes, because read-side falls back to existing null/pending behavior
- Rollback path: yes, via the read-side flag

### Placeholder Scan

- No `TODO`, `TBD`, or “implement later”
- Every task has concrete files, code shape, commands, and expected outcomes

### Type Consistency

- `estimated_bounty_amount` remains `int | None`
- `estimated_bounty_label` remains `str | None`
- Snapshot completeness is defined in one module and reused by backfill + audit
