"""
Apify – Instagram Scraper Connector
=====================================
Nutzt den offiziellen Apify-Actor "apify/instagram-scraper".
Ohne API-Key läuft ein Mock, der statische Dummy-Daten zurückgibt.

Apify Free Tier: https://apify.com/pricing
Actor-Doku:      https://apify.com/apify/instagram-scraper
"""

import httpx
from datetime import datetime, timezone
from typing import AsyncGenerator

from config import get_settings
from schemas.post import PostCreate
from models.db import ContentType, Platform

ACTOR_ID = "apify~instagram-scraper"
BASE_URL = "https://api.apify.com/v2"


async def fetch_public_profile(
    username: str,
    max_posts: int = 50,
) -> AsyncGenerator[PostCreate, None]:
    """
    Holt öffentliche Posts eines Instagram-Accounts via Apify.
    Ohne API-Token werden Mock-Daten geliefert.
    """
    settings = get_settings()

    if not settings.apify_api_token:
        async for post in _mock_posts(username, max_posts):
            yield post
        return

    # --- Apify Run starten ---
    async with httpx.AsyncClient(timeout=120) as client:
        run_resp = await client.post(
            f"{BASE_URL}/acts/{ACTOR_ID}/runs",
            headers={"Authorization": f"Bearer {settings.apify_api_token}"},
            json={
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsType": "posts",
                "resultsLimit": max_posts,
            },
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["data"]["id"]

        # Auf Abschluss warten (polling)
        import asyncio
        for _ in range(60):
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"{BASE_URL}/acts/{ACTOR_ID}/runs/{run_id}",
                headers={"Authorization": f"Bearer {settings.apify_api_token}"},
            )
            status = status_resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify run {run_id} ended with status: {status}")

        # Ergebnisse holen
        items_resp = await client.get(
            f"{BASE_URL}/acts/{ACTOR_ID}/runs/{run_id}/dataset/items",
            headers={"Authorization": f"Bearer {settings.apify_api_token}"},
            params={"format": "json"},
        )
        items_resp.raise_for_status()

        for item in items_resp.json():
            yield _map_item(item, username)


def _map_item(item: dict, account: str) -> PostCreate:
    ts_raw = item.get("timestamp") or item.get("taken_at_timestamp")
    posted_at = (
        datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        if isinstance(ts_raw, (int, float))
        else datetime.fromisoformat(ts_raw)
        if isinstance(ts_raw, str)
        else None
    )
    caption = item.get("caption") or item.get("text") or ""
    hashtags = [w for w in caption.split() if w.startswith("#")]
    return PostCreate(
        platform=Platform.INSTAGRAM,
        source_id=item.get("id") or item.get("shortCode") or str(hash(caption)),
        account=account,
        author_username=item.get("ownerUsername") or account,
        author_display_name=item.get("ownerFullName"),
        content_type=ContentType.POST,
        text=caption or None,
        posted_at=posted_at,
        likes_count=item.get("likesCount", 0) or 0,
        comments_count=item.get("commentsCount", 0) or 0,
        raw_data=item,
        meta={
            "hashtags": hashtags,
            "url": item.get("url"),
            "display_url": item.get("displayUrl"),
        },
    )


async def _mock_posts(username: str, count: int) -> AsyncGenerator[PostCreate, None]:
    """Dummy-Daten für Entwicklung ohne Apify-Key."""
    import random
    samples = [
        ("Toller Tag heute! #sun #happy", 42, 5),
        ("Neues Projekt gestartet 🚀 #work #tech", 18, 2),
        ("Kaffee und Code ☕ #coding #morning", 31, 7),
        ("Wochenend-Ausflug ins Grüne 🌿", 87, 12),
        ("Back to the grind #motivation", 14, 1),
    ]
    for i in range(min(count, len(samples))):
        text, likes, comments = samples[i]
        yield PostCreate(
            platform=Platform.INSTAGRAM,
            source_id=f"mock_{username}_{i}",
            account=username,
            author_username=username,
            content_type=ContentType.POST,
            text=text,
            posted_at=datetime(2024, 1, i + 1, 12, 0, tzinfo=timezone.utc),
            likes_count=likes,
            comments_count=comments,
            raw_data={"mock": True, "index": i},
            meta={"hashtags": [w for w in text.split() if w.startswith("#")]},
        )
