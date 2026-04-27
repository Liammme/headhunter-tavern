import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.market_intelligence_living_report_service import generate_living_market_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a living market report from market intelligence facts.")
    parser.add_argument("--mode", choices=("baseline", "update", "auto"), required=True)
    parser.add_argument("--days", type=int, choices=(180,), default=180)
    parser.add_argument("--force", action="store_true", help="Allow regenerating a baseline when a living report exists.")
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        summary = generate_living_market_report(db, mode=args.mode, days=args.days, force=args.force)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
