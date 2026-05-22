"""
Bluesky Connector via AT Protocol
====================================
Bluesky ist komplett offen – öffentliche Posts brauchen keinen Auth-Token.
Für den eigenen Feed oder zeitbasierte Suchen ist ein App-Password hilfreich.

atproto-Doku: https://atproto.blue/en/latest/
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from atproto import Client, models as at_models

from config import get_settings
from schemas.post import PostCreate
from models.db import ContentType, Platform


def _get_client() -> Client:
    s = get_settings()
    client = Client()
    if s.bluesky_handle and s.bluesky_app_password:
        client.login(s.bluesky_handle, s.bluesky_app_password)
    return client


def _parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_author_feed(
    handle: str,
    limit: int = 50,
) -> AsyncGenerator[PostCreate, None]:
    """
    Holt öffentliche Posts eines Bluesky-Accounts.
    handle: z.B. "bsky.app" oder "user.bsky.social"
    """
    client = _get_client()

    def _fetch():
        posts = []
        cursor = None
        while len(posts) < limit:
            batch_size = min(100, limit - len(posts))
            resp = client.get_author_feed(actor=handle, limit=batch_size, cursor=cursor)
            feed = resp.feed or []
            posts.extend(feed)
            cursor = resp.cursor
            if not cursor or not feed:
                break
        return posts

    feed_items = await asyncio.get_event_loop().run_in_executor(None, _fetch)

    for item in feed_items[:limit]:
        post = item.post
        record = post.record

        # Text extrahieren (unterschiedliche Record-Typen)
        text = getattr(record, "text", None)
        ts = _parse_timestamp(getattr(record, "created_at", None))

        # Likes / Replies
        like_count = getattr(post, "like_count", 0) or 0
        reply_count = getattr(post, "reply_count", 0) or 0
        repost_count = getattr(post, "repost_count", 0) or 0

        author = post.author
        author_handle = getattr(author, "handle", handle)
        author_display = getattr(author, "display_name", None)

        # URI als stable ID
        uri = post.uri  # z.B. at://did:plc:xxx/app.bsky.feed.post/yyy

        # Hashtags aus Facets (Bluesky's structured annotations)
        hashtags = []
        for facet in getattr(record, "facets", []) or []:
            for feature in facet.features:
                if hasattr(feature, "tag"):
                    hashtags.append(f"#{feature.tag}")

        yield PostCreate(
            platform=Platform.BLUESKY,
            source_id=uri,
            account=handle,
            author_username=author_handle,
            author_display_name=author_display,
            content_type=ContentType.POST,
            text=text,
            posted_at=ts,
            likes_count=like_count,
            comments_count=reply_count,
            shares_count=repost_count,
            raw_data={
                "uri": uri,
                "cid": post.cid,
                "text": text,
                "author_handle": author_handle,
                "like_count": like_count,
                "reply_count": reply_count,
                "repost_count": repost_count,
            },
            meta={"hashtags": hashtags},
        )


async def search_posts(
    query: str,
    limit: int = 50,
) -> AsyncGenerator[PostCreate, None]:
    """Bluesky-Volltextsuche (erfordert Auth)."""
    client = _get_client()

    def _fetch():
        resp = client.app.bsky.feed.search_posts({"q": query, "limit": min(limit, 100)})
        return resp.posts or []

    posts = await asyncio.get_event_loop().run_in_executor(None, _fetch)

    for post in posts[:limit]:
        record = post.record
        text = getattr(record, "text", None)
        ts = _parse_timestamp(getattr(record, "created_at", None))
        author = post.author

        yield PostCreate(
            platform=Platform.BLUESKY,
            source_id=post.uri,
            account=f"search:{query}",
            author_username=getattr(author, "handle", "unknown"),
            author_display_name=getattr(author, "display_name", None),
            content_type=ContentType.POST,
            text=text,
            posted_at=ts,
            likes_count=getattr(post, "like_count", 0) or 0,
            comments_count=getattr(post, "reply_count", 0) or 0,
            raw_data={"uri": post.uri, "text": text},
            meta={},
        )
