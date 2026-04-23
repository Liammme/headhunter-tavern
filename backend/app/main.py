import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import claims, company_clue, crawl, health, home
from app.core.config import parse_cors_origins, settings
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.bounty_readiness_service import audit_estimated_bounties

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    run_startup_audits()
    yield


app = FastAPI(title="Bounty Pool API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(home.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(company_clue.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")


def run_startup_audits() -> None:
    if not settings.bounty_pool_estimated_bounty_startup_audit_enabled:
        return

    try:
        with SessionLocal() as db:
            summary = audit_estimated_bounties(
                db,
                today=datetime.now().date(),
                window_days=settings.bounty_pool_estimated_bounty_audit_window_days,
            )
    except Exception:
        logger.warning("Estimated bounty startup audit failed", exc_info=True)
        return

    logger.info("Estimated bounty startup audit: %s", json.dumps(summary, ensure_ascii=False, sort_keys=True))
