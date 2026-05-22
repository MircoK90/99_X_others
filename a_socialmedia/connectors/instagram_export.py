"""
Instagram DSGVO-Export Parser
==============================
Instagram erlaubt einen vollständigen Daten-Export unter:
  Einstellungen → Dein Account → Deine Daten bei Instagram → Herunterladen

Das ZIP enthält u.a.:
  content/posts_1.json          – eigene Posts
  content/stories.json          – Stories
  comments/post_comments_1.json – eigene Kommentare unter fremden Posts
  likes/liked_posts.json        – gelikte Posts (nur Referenz, kein Text)
  messages/inbox/<name>/        – DMs (message_1.json, message_2.json, …)
  profile/profile_information.json

Dieser Parser liest das entpackte Verzeichnis und gibt PostCreate-Objekte zurück.
"""

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from schemas.post import PostCreate
from models.db import ContentType, Platform


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _ts(unix: int | None) -> datetime | None:
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc)


def _decode(text: str | None) -> str | None:
    """Instagram kodiert Texte manchmal als latin-1-escaped UTF-8."""
    if text is None:
        return None
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Einzelne Export-Typen
# ---------------------------------------------------------------------------

def _parse_posts(export_dir: Path, username: str) -> Generator[PostCreate, None, None]:
    """content/posts_1.json, posts_2.json, …"""
    idx = 1
    while True:
        data = _load_json(export_dir / "content" / f"posts_{idx}.json")
        if data is None:
            break
        for item in data:
            media_list = item.get("media", [item])  # manchmal flach, manchmal nested
            first = media_list[0] if media_list else item
            caption = _decode(first.get("title") or item.get("title", ""))
            ts = _ts(first.get("creation_timestamp"))
            hashtags = [w for w in (caption or "").split() if w.startswith("#")]
            yield PostCreate(
                platform=Platform.INSTAGRAM,
                source_id=first.get("uri", f"post_{ts}_{idx}"),
                account=username,
                author_username=username,
                content_type=ContentType.POST,
                text=caption or None,
                posted_at=ts,
                raw_data=item,
                meta={
                    "hashtags": hashtags,
                    "media_count": len(media_list),
                },
            )
        idx += 1


def _parse_stories(export_dir: Path, username: str) -> Generator[PostCreate, None, None]:
    data = _load_json(export_dir / "content" / "stories.json")
    if not data:
        return
    stories = data if isinstance(data, list) else data.get("ig_stories", [])
    for item in stories:
        ts = _ts(item.get("creation_timestamp"))
        caption = _decode(item.get("title", ""))
        yield PostCreate(
            platform=Platform.INSTAGRAM,
            source_id=item.get("uri", f"story_{ts}"),
            account=username,
            author_username=username,
            content_type=ContentType.STORY,
            text=caption or None,
            posted_at=ts,
            raw_data=item,
            meta={},
        )


def _parse_comments(export_dir: Path, username: str) -> Generator[PostCreate, None, None]:
    idx = 1
    while True:
        data = _load_json(export_dir / "comments" / f"post_comments_{idx}.json")
        if data is None:
            break
        items = data if isinstance(data, list) else []
        for item in items:
            # Struktur: {"string_map_data": {"Comment": {"value": "...", "timestamp": ...}}}
            smd = item.get("string_map_data", {})
            comment_obj = smd.get("Comment", {})
            text = _decode(comment_obj.get("value", ""))
            ts = _ts(comment_obj.get("timestamp"))
            yield PostCreate(
                platform=Platform.INSTAGRAM,
                source_id=f"comment_{username}_{ts}_{hash(text)}",
                account=username,
                author_username=username,
                content_type=ContentType.COMMENT,
                text=text or None,
                posted_at=ts,
                raw_data=item,
                meta={},
            )
        idx += 1


def _parse_likes(export_dir: Path, username: str) -> Generator[PostCreate, None, None]:
    """Gelikte Posts: kein Text, aber nützlich für Netzwerkanalyse."""
    data = _load_json(export_dir / "likes" / "liked_posts.json")
    if not data:
        return
    items = data if isinstance(data, list) else data.get("likes_media_likes", [])
    for item in items:
        smd = item.get("string_map_data", {})
        like_obj = smd.get("Like", smd.get("Saved", {}))
        ts = _ts(like_obj.get("timestamp"))
        href = like_obj.get("href", "")
        yield PostCreate(
            platform=Platform.INSTAGRAM,
            source_id=f"like_{username}_{ts}_{hash(href)}",
            account=username,
            author_username=username,
            content_type=ContentType.LIKE,
            text=None,
            posted_at=ts,
            raw_data=item,
            meta={"href": href},
        )


def _parse_dms(export_dir: Path, username: str) -> Generator[PostCreate, None, None]:
    inbox_dir = export_dir / "messages" / "inbox"
    if not inbox_dir.exists():
        return
    for conv_dir in inbox_dir.iterdir():
        if not conv_dir.is_dir():
            continue
        idx = 1
        while True:
            data = _load_json(conv_dir / f"message_{idx}.json")
            if data is None:
                break
            for msg in data.get("messages", []):
                sender = _decode(msg.get("sender_name", ""))
                text = _decode(msg.get("content", ""))
                ts = _ts(msg.get("timestamp_ms", 0) // 1000 if msg.get("timestamp_ms") else None)
                yield PostCreate(
                    platform=Platform.INSTAGRAM,
                    source_id=f"dm_{conv_dir.name}_{ts}_{hash(text)}",
                    account=username,
                    author_username=sender,
                    content_type=ContentType.DM,
                    text=text or None,
                    posted_at=ts,
                    raw_data=msg,
                    meta={"conversation": conv_dir.name},
                )
            idx += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_export(
    source: Path | str,
    username: str,
    include: set[str] | None = None,
) -> Generator[PostCreate, None, None]:
    """
    Parst einen Instagram DSGVO-Export.

    Args:
        source:   Pfad zum entpackten Ordner ODER zum ZIP-Archiv.
        username: Dein Instagram-Handle (steht in profile_information.json).
        include:  Welche Typen einschließen? {"posts","stories","comments","likes","dms"}
                  None = alles.
    """
    include = include or {"posts", "stories", "comments", "likes", "dms"}
    export_dir = Path(source)

    # ZIP auto-extract in temporäres Verzeichnis
    if export_dir.suffix == ".zip":
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(export_dir, "r") as zf:
                zf.extractall(tmp)
            # Instagram legt alles in einen Unterordner
            subdirs = [p for p in tmp.iterdir() if p.is_dir()]
            export_dir = subdirs[0] if subdirs else tmp
            yield from parse_export(export_dir, username, include)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return

    # Auto-detect username aus Export falls nicht angegeben
    if not username:
        profile = _load_json(export_dir / "profile" / "profile_information.json")
        if profile:
            username = profile.get("profile_user", [{}])[0].get("string_map_data", {}).get(
                "Username", {}
            ).get("value", "unknown")

    if "posts" in include:
        yield from _parse_posts(export_dir, username)
    if "stories" in include:
        yield from _parse_stories(export_dir, username)
    if "comments" in include:
        yield from _parse_comments(export_dir, username)
    if "likes" in include:
        yield from _parse_likes(export_dir, username)
    if "dms" in include:
        yield from _parse_dms(export_dir, username)
