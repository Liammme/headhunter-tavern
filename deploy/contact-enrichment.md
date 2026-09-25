# Source health and company contact enrichment

This release changes the Talent Signal source backend. Cold Email continues using
the existing authenticated BD contact API; it needs no schema or API changes.

## Behavior

- Open Robotics and PyTorch use their public category RSS feeds. Each adapter
  makes one request instead of a category request plus a request for every post.
  Hiring posts without an email are retained as job signals.
- The obsolete `aijobsnet` parser and production-blocked `workatstartup_ai`
  listing are disabled explicitly. Their names and reasons remain in the daily
  summary. No anti-bot bypass or paid provider is introduced.
- `source_health` distinguishes `ok`, `empty`, `error`, and `disabled`.
  An empty result is a diagnostic state, not proof that the source has failed.
  Compare consecutive daily summaries to identify prolonged empty results.
- Global and Japan crawl writes are serialized by a PostgreSQL advisory lock.
  The Japan cron template moves to 08:20 and 14:20 to reduce contention.
- After the global crawl, a separate enrichment service checks source-supplied
  company websites for jobs lacking a direct email. It follows at most three
  same-host home/contact/about/team pages, up to ten websites per run and ten
  published email candidates per website. Successful
  and empty checks are retried after seven days; errors after one day.
- Only published same-host email addresses are accepted (`www` is equivalent).
  Job boards, social sites, unrelated domains, application-only and technical
  inbox names are excluded. No guessed email addresses are generated.
- URLs are limited to public HTTP(S) addresses and ports 80/443. Requests pin the
  validated IP while retaining TLS hostname verification, limit response size,
  and reject cross-company redirects. Private DNS results are rejected.
- Contact evidence and check status are persisted in `jobs.signal_tags` under
  `contact_enrichment`. Existing contact refreshes consume that evidence, so a
  later crawl does not immediately remove website-derived contacts. Changing or
  removing the source company URL, or changing company identity, invalidates it.
- A failed enrichment stage does not undo the already committed jobs. The daily
  summary includes `contact_enrichment` counts and errors as well as source health.

The source company URL is a lead, not independently proven company ownership.
Published addresses are not verified for SMTP deliverability, decision-making
authority, or permission to receive outreach. Existing Cold Email research and
approval still apply. Jobs without a reliable company URL remain un-enriched;
there is no paid directory or company-name search in this release. More jobs or
discovered emails do not guarantee new customers after downstream deduplication.

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `BOUNTY_POOL_CONTACT_ENRICHMENT_ENABLED` | `true` | Enable enrichment after global crawl |
| `BOUNTY_POOL_CONTACT_ENRICHMENT_MAX_DOMAINS` | `10` | Website checks per run (0–50) |
| `BOUNTY_POOL_CONTACT_ENRICHMENT_RETRY_DAYS` | `7` | Successful/empty check interval (1–30 days) |
| `BOUNTY_POOL_CONTACT_ENRICHMENT_TIMEOUT_SECONDS` | `10` | Network timeout per request phase (1–30 seconds) |

There are no new dependencies, tables, secrets, or paid API requirements.
The enrichment limit is per run, not per day. Multiple new jobs at the same
website in one run share a lookup; newly arriving jobs may cause another lookup
in a later run.

## Branch validation (2026-09-25)

- Related regression suite: 66 passed. Final focused website/lock suite after
  review fixes: 13 passed (overlaps the regression suite). Compilation and
  `git diff --check` passed.
- Public RSS smoke test: Open Robotics returned 25 matching job signals;
  PyTorch returned 21. These counts do not establish new customer counts.
- Three DeJob website samples: two returned no eligible public email; one was
  rejected by URL/content validation. No production database writes or emails
  were made during these smoke tests.
- PostgreSQL lock behavior is covered with simulated connections, including
  exceptions and failed unlock. Real PostgreSQL concurrency is still a release
  check: no local PostgreSQL server or running Docker daemon was available.
- The source restoration and enrichment have not yet been verified from the
  production server or through a complete production Cold Email sync.

Changed files:

- Configuration: `backend/app/core/config.py`.
- Sources: `backend/app/crawlers/registry.py`,
  `backend/app/crawlers/adapters/discourse_ai_jobs.py`.
- Services: `backend/app/services/company_contact_enrichment.py`,
  `crawl_run_lock.py`, `crawl_fetch_service.py`, `crawl_pipeline.py`,
  `japan_crawl_pipeline.py`, `daily_bounty_service.py`,
  `bd_contact_extraction.py`, `job_upsert_service.py`.
- Tests: `backend/tests/test_company_contact_enrichment.py`,
  `test_crawl_run_lock.py`, `test_crawl_fetch_service.py`, `test_crawl_pipeline.py`,
  `test_daily_bounty_service.py`, `test_discourse_ai_job_adapters.py`,
  `test_bd_contact_service.py`, `test_job_upsert_service.py`, `test_config.py`.
- Operations: `deploy/README.md`, `deploy/cron/japan-market.cron`, this document.

## Release checks (after branch approval)

1. Deploy the approved revision of this repository using the existing backend
   release procedure. Replace the existing Japan cron entry with the revised
   template; do not add a second schedule.
2. On local PostgreSQL/staging, verify two simultaneous crawls wait for each
   other and leave no duplicate jobs or contacts. SQLite does not emulate the
   PostgreSQL advisory lock.
3. Run `python -m app.cli.daily_bounty` once and inspect `source_health`,
   `disabled_sources`, `contact_enrichment`, and `errors` in the JSON summary.
4. Confirm that website-derived contacts have evidence URLs and appear through
   the existing authenticated BD contact API. Do not expose credentials or
   full contact data in deployment logs.
5. After the next Cold Email sync, compare newly discovered emails against that
   account's existing customers. Validate actual new customers separately from
   new jobs or repeated emails.

To stop website requests, set `BOUNTY_POOL_CONTACT_ENRICHMENT_ENABLED=false` in
the source backend configuration and restart its service; cron loads the same
configuration on its next run. Existing contacts are retained. A code rollback
requires no database migration; older contact refresh code will not consume the
stored website enrichment and can mark those derived contacts stale.
