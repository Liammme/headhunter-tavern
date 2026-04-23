from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.bounty_readiness_service import audit_estimated_bounties


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-readiness", action="store_true")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        summary = audit_estimated_bounties(
            db,
            today=datetime.now().date(),
            window_days=settings.bounty_pool_estimated_bounty_audit_window_days,
        )

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if args.strict_readiness and not summary["strict_readiness"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
