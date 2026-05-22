"""Social Pipeline – FastAPI App Entry Point"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import ingest, data

settings = get_settings()

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Social Pipeline",
    description="Ingest & query social media data from Instagram, Reddit, Bluesky, YouTube.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # für lokale Entwicklung; in Prod einschränken
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(data.router)


@app.on_event("startup")
async def startup() -> None:
    log.info("Initializing database…")
    await init_db()
    log.info("Database ready.")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
