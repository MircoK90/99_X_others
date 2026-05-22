"""
Ingest-Router
==============
Endpoints zum Befüllen der Datenbank aus allen Quellen.

POST /ingest/instagram/export   – DSGVO-ZIP hochladen
POST /ingest/instagram/apify    – öffentliches Profil via Apify
POST /ingest/reddit             – Subreddit
POST /ingest/bluesky            – Bluesky-Handle
POST /ingest/youtube            – YouTube-Video-Kommentare
"""

import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import get_db
from models.db import Post
from schemas.post import (
    ApifyIngestRequest,
    BlueskyIngestRequest,
    IngestResult,
    PostCreate,
    RedditIngestRequest,
    YouTubeIngestRequest,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Hilfsfunktion: PostCreate → DB (upsert, ignoriert Duplikate)
# ---------------------------------------------------------------------------

async def _bulk_upsert(posts: list[PostCreate], db: AsyncSession) -> tuple[int, int]:
    if not posts:
        return 0, 0

    inserted = 0
    skipped = 0
    for post in posts:
        stmt = (
            pg_insert(Post)
            .values(**post.model_dump())
            .on_conflict_do_nothing(constraint="uq_platform_source")
        )
        result = await db.execute(stmt)
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


# ---------------------------------------------------------------------------
# Instagram – DSGVO Export (ZIP Upload)
# ---------------------------------------------------------------------------

@router.post("/instagram/export", response_model=IngestResult)
async def ingest_instagram_export(
    file: UploadFile = File(..., description="Instagram DSGVO Export als ZIP"),
    username: str = Form(..., description="Dein Instagram-Handle"),
    include: str = Form(
        default="posts,stories,comments,likes,dms",
        description="Komma-getrennte Liste: posts,stories,comments,likes,dms",
    ),
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """
    Lade deinen Instagram DSGVO-Export (ZIP) hoch.
    Holen unter: Einstellungen → Dein Account → Deine Daten → Herunterladen
    """
    from connectors.instagram_export import parse_export

    include_set = {s.strip() for s in include.split(",")}

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        posts = list(parse_export(tmp_path, username=username, include=include_set))
    finally:
        tmp_path.unlink(missing_ok=True)

    inserted, skipped = await _bulk_upsert(posts, db)
    return IngestResult(inserted=inserted, skipped=skipped, source="instagram_export")


# ---------------------------------------------------------------------------
# Instagram – Apify (öffentliches Profil)
# ---------------------------------------------------------------------------

@router.post("/instagram/apify", response_model=IngestResult)
async def ingest_instagram_apify(
    req: ApifyIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Holt öffentliche Posts eines Instagram-Accounts via Apify."""
    from connectors.apify import fetch_public_profile

    posts = []
    async for post in fetch_public_profile(req.username, req.max_posts):
        posts.append(post)

    inserted, skipped = await _bulk_upsert(posts, db)
    return IngestResult(inserted=inserted, skipped=skipped, source=f"apify:{req.username}")


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

@router.post("/reddit", response_model=IngestResult)
async def ingest_reddit(
    req: RedditIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Holt Posts aus einem Subreddit."""
    from connectors.reddit import fetch_subreddit

    posts = []
    async for post in fetch_subreddit(req.subreddit, req.limit, req.sort):
        posts.append(post)

    inserted, skipped = await _bulk_upsert(posts, db)
    return IngestResult(inserted=inserted, skipped=skipped, source=f"reddit:r/{req.subreddit}")


# ---------------------------------------------------------------------------
# Bluesky
# ---------------------------------------------------------------------------

@router.post("/bluesky", response_model=IngestResult)
async def ingest_bluesky(
    req: BlueskyIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Holt öffentliche Posts eines Bluesky-Accounts."""
    from connectors.bluesky import fetch_author_feed

    posts = []
    async for post in fetch_author_feed(req.handle, req.limit):
        posts.append(post)

    inserted, skipped = await _bulk_upsert(posts, db)
    return IngestResult(inserted=inserted, skipped=skipped, source=f"bluesky:{req.handle}")


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------

@router.post("/youtube", response_model=IngestResult)
async def ingest_youtube(
    req: YouTubeIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Holt Video-Metadaten und Kommentare eines YouTube-Videos."""
    from connectors.youtube import fetch_video_comments

    posts = []
    async for post in fetch_video_comments(req.video_id, req.max_comments):
        posts.append(post)

    inserted, skipped = await _bulk_upsert(posts, db)
    return IngestResult(inserted=inserted, skipped=skipped, source=f"youtube:{req.video_id}")
