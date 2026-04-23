# Production Deployment Templates

These templates are the minimum production artifacts for the recommended setup:

- `systemd/bounty-pool.service`: FastAPI process management
- `nginx/bounty-pool.conf`: reverse proxy for `api.your-domain.com`
- `cron/daily-bounty.cron`: daily `daily_bounty` schedule example

Adjust paths, domain names, and secrets before using them on the server.
