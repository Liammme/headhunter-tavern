import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.market_intelligence_baseline_service import generate_market_baseline_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a baseline market intelligence report from facts.")
    parser.add_argument("--days", type=int, choices=(30, 90, 180), required=True)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        summary = generate_market_baseline_report(db, days=args.days)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
