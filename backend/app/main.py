from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import claims, crawl, health, home

app = FastAPI(title="Bounty Pool API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(home.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")
