from __future__ import annotations

import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.daily_bounty_service import run_daily_bounty_generation


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        summary = run_daily_bounty_generation(db)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
