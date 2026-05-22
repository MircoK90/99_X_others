"""
YouTube Connector via yt-dlp + YouTube Data API v3
=====================================================
Zwei Modi:
  1. yt-dlp  → Metadaten & Kommentare ohne API-Key (aber langsamer)
  2. YouTube Data API v3 → schneller, strukturierter, braucht API-Key

API-Key erstellen: https://console.cloud.google.com
  → APIs & Services → YouTube Data API v3 aktivieren → Credentials → API Key
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from config import get_settings
from schemas.post import PostCreate
from models.db import ContentType, Platform


# ---------------------------------------------------------------------------
# Modus 1: yt-dlp (kein API-Key nötig)
# ---------------------------------------------------------------------------

async def fetch_video_comments_ytdlp(
    video_id: str,
    max_comments: int = 200,
) -> AsyncGenerator[PostCreate, None]:
    """
    Holt Kommentare eines YouTube-Videos via yt-dlp.
    Kein API-Key nötig, aber langsamer und braucht yt-dlp installiert.
    """
    import yt_dlp

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "skip_download": True,
        "getcomments": True,
        "extractor_args": {"youtube": {"max_comments": [str(max_comments)]}},
        "quiet": True,
    }

    def _fetch() -> dict:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False) or {}

    info = await asyncio.get_event_loop().run_in_executor(None, _fetch)

    # Video selbst als Post
    title = info.get("title", "")
    description = info.get("description", "")
    upload_date = info.get("upload_date")  # "YYYYMMDD"
    ts = (
        datetime(int(upload_date[:4]), int(upload_date[4:6]), int(upload_date[6:8]), tzinfo=timezone.utc)
        if upload_date and len(upload_date) == 8
        else None
    )

    yield PostCreate(
        platform=Platform.YOUTUBE,
        source_id=video_id,
        account=info.get("uploader_id") or info.get("channel_id") or "unknown",
        author_username=info.get("uploader_id"),
        author_display_name=info.get("uploader"),
        content_type=ContentType.VIDEO,
        text=f"{title}\n\n{description}".strip() or None,
        posted_at=ts,
        likes_count=info.get("like_count") or 0,
        comments_count=info.get("comment_count") or 0,
        raw_data={
            "id": video_id,
            "title": title,
            "channel": info.get("channel"),
            "view_count": info.get("view_count"),
            "duration": info.get("duration"),
            "tags": info.get("tags", []),
        },
        meta={
            "tags": info.get("tags", []),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
        },
    )

    # Kommentare
    for c in (info.get("comments") or [])[:max_comments]:
        c_ts_raw = c.get("timestamp")
        c_ts = datetime.fromtimestamp(c_ts_raw, tz=timezone.utc) if c_ts_raw else None
        text = c.get("text", "")
        yield PostCreate(
            platform=Platform.YOUTUBE,
            source_id=c.get("id") or f"yt_comment_{video_id}_{hash(text)}",
            account=video_id,
            author_username=c.get("author_id"),
            author_display_name=c.get("author"),
            content_type=ContentType.COMMENT,
            text=text or None,
            posted_at=c_ts,
            likes_count=c.get("like_count") or 0,
            raw_data=c,
            meta={"parent_id": c.get("parent")},
        )


# ---------------------------------------------------------------------------
# Modus 2: YouTube Data API v3
# ---------------------------------------------------------------------------

async def fetch_video_comments_api(
    video_id: str,
    max_comments: int = 200,
) -> AsyncGenerator[PostCreate, None]:
    """
    Holt Kommentare via YouTube Data API v3.
    Schneller und strukturierter, braucht einen API-Key.
    """
    import httpx

    settings = get_settings()
    if not settings.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY nicht gesetzt – nutze fetch_video_comments_ytdlp stattdessen.")

    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "key": settings.youtube_api_key,
        "videoId": video_id,
        "part": "snippet",
        "maxResults": 100,
        "textFormat": "plainText",
    }

    collected = 0
    async with httpx.AsyncClient() as client:
        while collected < max_comments:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for thread in data.get("items", []):
                top = thread["snippet"]["topLevelComment"]["snippet"]
                ts_str = top.get("publishedAt")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else None

                yield PostCreate(
                    platform=Platform.YOUTUBE,
                    source_id=thread["id"],
                    account=video_id,
                    author_username=top.get("authorChannelId", {}).get("value"),
                    author_display_name=top.get("authorDisplayName"),
                    content_type=ContentType.COMMENT,
                    text=top.get("textDisplay") or None,
                    posted_at=ts,
                    likes_count=top.get("likeCount", 0),
                    raw_data=thread,
                    meta={"reply_count": thread["snippet"].get("totalReplyCount", 0)},
                )
                collected += 1
                if collected >= max_comments:
                    return

            next_page = data.get("nextPageToken")
            if not next_page:
                break
            params["pageToken"] = next_page


async def fetch_video_comments(
    video_id: str,
    max_comments: int = 200,
) -> AsyncGenerator[PostCreate, None]:
    """Auto-select: API wenn Key vorhanden, sonst yt-dlp."""
    settings = get_settings()
    if settings.youtube_api_key:
        async for post in fetch_video_comments_api(video_id, max_comments):
            yield post
    else:
        async for post in fetch_video_comments_ytdlp(video_id, max_comments):
            yield post
