import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.market_intelligence_snapshot_service import generate_daily_market_intelligence_snapshot
from app.services.region import JAPAN_REGION


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Japan market intelligence snapshot.")
    parser.add_argument("--days", type=int, choices=(30, 90, 180), default=90)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        summary = generate_daily_market_intelligence_snapshot(db, region=JAPAN_REGION, window_days=args.days)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
