# Production Deployment Templates

This directory contains the minimum production artifacts for the recommended backend setup:

- `systemd/bounty-pool.service`
  - Runs the FastAPI backend with `uvicorn`
  - Loads backend environment variables from `.env`
- `nginx/bounty-pool.conf`
  - Proxies `api.your-domain.com` to the local FastAPI process
- `cron/daily-bounty.cron`
  - Runs `python -m app.cli.daily_bounty` every day at 08:00 and 14:00
  - Uses `/etc/cron.d` format and runs as the `deploy` user
- `cron/living-market-report.cron`
  - Runs `python -m app.cli.refresh_living_market_report` every day at 15:30
  - Refreshes sanitized market facts idempotently, then generates a Living Report only when the latest successful report is at least 3 calendar days old
  - Uses `/etc/cron.d` format and runs as the `deploy` user
- `backend-deploy.sh`
  - Pulls the latest `master`, restarts the backend service, and runs health checks
- `tencent-cloud-postgres.md`
  - Beginner-friendly deployment guide for Tencent Cloud CVM + Postgres + systemd + nginx + cron
- `ops-runbook.md`
  - Post-launch operations and release checklist for the production backend

Recommended usage order:

1. Follow `tencent-cloud-postgres.md` to prepare the server, Postgres, Python environment, and `.env`.
2. Copy `systemd/bounty-pool.service` to `/etc/systemd/system/` and adjust paths.
3. Copy `nginx/bounty-pool.conf` to `/etc/nginx/sites-available/` and adjust the domain.
4. Install `cron/daily-bounty.cron` after `daily_bounty` has been verified manually once.
5. Install `cron/living-market-report.cron` after `refresh_living_market_report` has been verified manually once.
6. Use `backend-deploy.sh` for routine backend releases after code is merged to `master`.
7. Use `ops-runbook.md` as the default manual for restarts, log checks, daily inspection, and release steps.

Routine backend release:

```bash
ssh deploy@43.163.127.112
bash /opt/bounty-pool/app/deploy/backend-deploy.sh
```

Schema-changing backend release:

`deploy/backend-deploy.sh` only pulls code, restarts `bounty-pool`, and checks `/health`. It does not initialize or migrate the database, so do not use the script alone for a release that adds schema.

The market intelligence layer release adds one PostgreSQL table: `market_intelligence_snapshots`. This is a new table and does not ALTER existing tables. Before or during production release, run this on the server:

```bash
cd /opt/bounty-pool/app/backend
source /opt/bounty-pool/venv/bin/activate
python -c "from app.db.init_db import init_db; init_db()"
```

After the schema step, restart `bounty-pool`, run health checks, manually run `python -m app.cli.daily_bounty`, curl `/api/v1/home`, and confirm the returned `intelligence` text does not include source/link/full JD/bounty/claim/BD language. If market intelligence generation fails, keep the service online and fall back to the old home logic or latest successful snapshot; do not delete `market_intelligence_snapshots` during an incident.

For local development, prefer local PostgreSQL and never point local `DATABASE_URL` at production. SQLite can stay in pytest fixtures, but do a local PostgreSQL smoke test before release. If there are no Python or Node dependency changes, skip extra `pip` or `npm` install steps; install dependencies only when `pyproject` or package files change.

Adjust paths, domain names, database credentials, and API keys before using them on the server.
