"""
Data-Router
============
Lese-Endpoints zum Abfragen der ingested Posts.

GET /posts          – Liste mit Filtern
GET /posts/{id}     – Einzelner Post
GET /stats          – Aggregierte Übersicht
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.db import ContentType, Platform, Post
from schemas.post import PostOut

router = APIRouter(prefix="/posts", tags=["data"])


@router.get("", response_model=list[PostOut])
async def list_posts(
    platform: Platform | None = Query(None),
    content_type: ContentType | None = Query(None),
    account: str | None = Query(None, description="Account-Name / Subreddit / Handle"),
    author: str | None = Query(None, description="Autor-Username"),
    since: datetime | None = Query(None, description="ISO-Datum, z.B. 2024-01-01T00:00:00Z"),
    until: datetime | None = Query(None),
    search: str | None = Query(None, description="Freitext-Suche im post.text"),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
) -> list[PostOut]:
    q = select(Post).order_by(Post.posted_at.desc().nullslast())

    if platform:
        q = q.where(Post.platform == platform)
    if content_type:
        q = q.where(Post.content_type == content_type)
    if account:
        q = q.where(Post.account == account)
    if author:
        q = q.where(Post.author_username == author)
    if since:
        q = q.where(Post.posted_at >= since)
    if until:
        q = q.where(Post.posted_at <= until)
    if search:
        q = q.where(Post.text.ilike(f"%{search}%"))

    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Schnelle Übersicht: wie viele Posts pro Plattform und Typ."""
    result = await db.execute(
        select(
            Post.platform,
            Post.content_type,
            func.count().label("count"),
            func.sum(Post.likes_count).label("total_likes"),
        ).group_by(Post.platform, Post.content_type)
    )
    rows = result.all()
    return {
        "total": sum(r.count for r in rows),
        "by_platform": {
            platform: sum(r.count for r in rows if r.platform == platform)
            for platform in {r.platform for r in rows}
        },
        "detail": [
            {
                "platform": r.platform,
                "content_type": r.content_type,
                "count": r.count,
                "total_likes": int(r.total_likes or 0),
            }
            for r in rows
        ],
    }


@router.get("/{post_id}", response_model=PostOut)
async def get_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PostOut:
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
