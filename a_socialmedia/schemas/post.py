"""Pydantic-Schemas für API-Requests und -Responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.db import ContentType, Platform


# ---------------------------------------------------------------------------
# Intern: was Connectors an die DB übergeben
# ---------------------------------------------------------------------------

class PostCreate(BaseModel):
    platform: Platform
    source_id: str
    account: str
    author_username: str | None = None
    author_display_name: str | None = None
    content_type: ContentType
    text: str | None = None
    language: str | None = None
    posted_at: datetime | None = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    raw_data: dict = {}
    meta: dict = {}


# ---------------------------------------------------------------------------
# API Response
# ---------------------------------------------------------------------------

class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: Platform
    source_id: str
    account: str
    author_username: str | None
    author_display_name: str | None
    content_type: ContentType
    text: str | None
    language: str | None
    posted_at: datetime | None
    ingested_at: datetime
    likes_count: int
    comments_count: int
    shares_count: int
    meta: dict


# ---------------------------------------------------------------------------
# Ingest-Requests
# ---------------------------------------------------------------------------

class RedditIngestRequest(BaseModel):
    subreddit: str
    limit: int = 100
    sort: str = "new"          # new | hot | top | rising


class BlueskyIngestRequest(BaseModel):
    handle: str                # z.B. "user.bsky.social"
    limit: int = 50


class YouTubeIngestRequest(BaseModel):
    video_id: str
    max_comments: int = 200


class ApifyIngestRequest(BaseModel):
    username: str              # Instagram-Handle (öffentlich)
    max_posts: int = 50


# ---------------------------------------------------------------------------
# Generic Response
# ---------------------------------------------------------------------------

class IngestResult(BaseModel):
    inserted: int
    skipped: int              # Duplikate
    source: str
