import argparse

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.bd_contact_service import backfill_bd_contacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill BD contact points from stored jobs.")
    parser.add_argument("--region", choices=["global", "japan"], default=None)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        result = backfill_bd_contacts(db, region=args.region)

    print(result)


if __name__ == "__main__":
    main()
