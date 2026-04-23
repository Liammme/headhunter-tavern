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
