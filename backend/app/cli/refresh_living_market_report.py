import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.market_intelligence_living_refresh_service import refresh_living_market_report_if_due


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Refresh living market report only when it is due.")
    parser.add_argument("--days", type=int, choices=(180,), default=180)
    parser.add_argument("--min-age-days", type=int, default=3)
    args = parser.parse_args(argv)
    if args.min_age_days < 1:
        parser.error("--min-age-days must be at least 1")

    init_db()
    with SessionLocal() as db:
        summary = refresh_living_market_report_if_due(
            db,
            days=args.days,
            min_age_days=args.min_age_days,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
