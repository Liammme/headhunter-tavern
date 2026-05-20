import json

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.japan_crawl_pipeline import run_japan_crawl


def main() -> None:
    init_db()
    with SessionLocal() as db:
        summary = run_japan_crawl(db)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
