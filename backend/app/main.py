from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import claims, company_clue, crawl, health, home
from app.core.config import parse_cors_origins, settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
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
