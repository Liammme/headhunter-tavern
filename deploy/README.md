# Production Deployment Templates

This directory contains the minimum production artifacts for the recommended backend setup:

- `systemd/bounty-pool.service`
  - Runs the FastAPI backend with `uvicorn`
  - Loads backend environment variables from `.env`
- `nginx/bounty-pool.conf`
  - Proxies `api.your-domain.com` to the local FastAPI process
- `cron/daily-bounty.cron`
  - Runs `python -m app.cli.daily_bounty` every day at 08:00
- `tencent-cloud-postgres.md`
  - Beginner-friendly deployment guide for Tencent Cloud CVM + Postgres + systemd + nginx + cron
- `ops-runbook.md`
  - Post-launch operations and release checklist for the production backend

Recommended usage order:

1. Follow `tencent-cloud-postgres.md` to prepare the server, Postgres, Python environment, and `.env`.
2. Copy `systemd/bounty-pool.service` to `/etc/systemd/system/` and adjust paths.
3. Copy `nginx/bounty-pool.conf` to `/etc/nginx/sites-available/` and adjust the domain.
4. Install `cron/daily-bounty.cron` after `daily_bounty` has been verified manually once.
5. Use `ops-runbook.md` as the default manual for restarts, log checks, daily inspection, and release steps.

Adjust paths, domain names, database credentials, and API keys before using them on the server.
