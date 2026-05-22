"""
Reddit Connector via PRAW
===========================
Holt Posts und Kommentare aus öffentlichen Subreddits oder User-Profilen.

App erstellen: https://www.reddit.com/prefs/apps  (Typ: "script")
Doku:          https://praw.readthedocs.io/
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

import praw
from praw.models import Submission, Comment

from config import get_settings
from schemas.post import PostCreate
from models.db import ContentType, Platform


def _get_reddit() -> praw.Reddit:
    s = get_settings()
    return praw.Reddit(
        client_id=s.reddit_client_id,
        client_secret=s.reddit_client_secret,
        user_agent=s.reddit_user_agent,
        # read-only, kein Login nötig
    )


async def fetch_subreddit(
    subreddit: str,
    limit: int = 100,
    sort: str = "new",          # new | hot | top | rising
) -> AsyncGenerator[PostCreate, None]:
    """
    Holt Submissions (Threads) aus einem Subreddit.
    sort="new" liefert die aktuellsten, "top" die meist-gevoteten.
    """
    reddit = _get_reddit()

    def _fetch() -> list[Submission]:
        sub = reddit.subreddit(subreddit)
        listing = {
            "new": sub.new,
            "hot": sub.hot,
            "top": sub.top,
            "rising": sub.rising,
        }.get(sort, sub.new)
        return list(listing(limit=limit))

    submissions = await asyncio.get_event_loop().run_in_executor(None, _fetch)

    for s in submissions:
        yield PostCreate(
            platform=Platform.REDDIT,
            source_id=s.id,
            account=f"r/{subreddit}",
            author_username=str(s.author) if s.author else "[deleted]",
            content_type=ContentType.THREAD,
            text=(s.selftext or s.title or "").strip() or s.title,
            posted_at=datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
            likes_count=s.score,
            comments_count=s.num_comments,
            raw_data={
                "id": s.id,
                "title": s.title,
                "selftext": s.selftext,
                "url": s.url,
                "subreddit": subreddit,
                "score": s.score,
                "upvote_ratio": s.upvote_ratio,
                "flair": s.link_flair_text,
            },
            meta={
                "title": s.title,
                "url": s.url,
                "flair": s.link_flair_text,
                "upvote_ratio": s.upvote_ratio,
            },
        )


async def fetch_submission_comments(
    submission_id: str,
    max_comments: int = 200,
) -> AsyncGenerator[PostCreate, None]:
    """Holt alle Kommentare eines Reddit-Threads (flach, erster Level)."""
    reddit = _get_reddit()

    def _fetch():
        submission = reddit.submission(id=submission_id)
        submission.comments.replace_more(limit=0)  # keine MoreComments expandieren
        return list(submission.comments.list())[:max_comments]

    comments = await asyncio.get_event_loop().run_in_executor(None, _fetch)

    for c in comments:
        if not isinstance(c, Comment):
            continue
        yield PostCreate(
            platform=Platform.REDDIT,
            source_id=c.id,
            account=f"submission/{submission_id}",
            author_username=str(c.author) if c.author else "[deleted]",
            content_type=ContentType.COMMENT,
            text=c.body or None,
            posted_at=datetime.fromtimestamp(c.created_utc, tz=timezone.utc),
            likes_count=c.score,
            raw_data={
                "id": c.id,
                "body": c.body,
                "score": c.score,
                "parent_id": c.parent_id,
                "submission_id": submission_id,
            },
            meta={"parent_id": c.parent_id},
        )
