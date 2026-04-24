# Bounty Pool

Minimal bootstrap for the Bounty Pool stack.

## Stack

- Backend: FastAPI
- Frontend: Next.js + React + TypeScript

## Layout

- `backend/` Python API service
- `frontend/` Next.js app scaffold

## Health check

Run the backend test from the repo root:

```bash
python -m pytest backend/tests/test_health.py
```
