import argparse
import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.crawlers.japan_registry import JAPAN_ADAPTERS
from app.services.market_intelligence_living_refresh_service import refresh_living_market_report_if_due
from app.services.region import JAPAN_REGION


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Japan living market intelligence snapshot.",
        epilog=(
            "Production sequence: python -m app.db.init_db; "
            "python -m app.cli.crawl_japan_jobs; "
            "python -m app.cli.generate_japan_market_report --days 180; "
            "sudo systemctl restart bounty-pool"
        ),
    )
    parser.add_argument("--days", type=int, choices=(180,), default=180)
    parser.add_argument("--min-age-days", type=int, default=0)
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        adapters = [adapter_class() for adapter_class in JAPAN_ADAPTERS.values()]
        summary = refresh_living_market_report_if_due(
            db,
            days=args.days,
            min_age_days=args.min_age_days,
            region=JAPAN_REGION,
            adapters=adapters,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
