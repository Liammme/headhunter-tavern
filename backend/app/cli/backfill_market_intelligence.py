import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.market_intelligence_fact_service import backfill_market_intelligence_facts


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill sanitized market intelligence facts.")
    parser.add_argument("--days", type=int, choices=(30, 90, 180), required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        summary = backfill_market_intelligence_facts(
            db,
            days=args.days,
            dry_run=args.dry_run,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
