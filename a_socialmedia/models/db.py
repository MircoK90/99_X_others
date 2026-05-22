"""SQLAlchemy ORM-Modelle – eine einheitliche Tabelle für alle Plattformen."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Platform(str, PyEnum):
    INSTAGRAM = "instagram"
    REDDIT = "reddit"
    BLUESKY = "bluesky"
    YOUTUBE = "youtube"


class ContentType(str, PyEnum):
    POST = "post"
    STORY = "story"
    REEL = "reel"
    COMMENT = "comment"
    DM = "dm"
    LIKE = "like"          # Nur Referenz, kein Text
    VIDEO = "video"
    THREAD = "thread"      # Reddit-Thread / Bluesky-Thread-Root


class Post(Base):
    """
    Normalisierter Datensatz – ein Row = ein Inhaltselement von einer Plattform.

    raw_data  → originales JSON, nichts weggeworfen
    meta      → vorberechnete Felder (likes, comments_count, …) für schnelle Queries
    """

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Quelle
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(512), nullable=False)
    """Originalkey der Plattform (Post-ID, Shortcode, URI, …)"""

    # Wessen Daten? (Account-Name / Subreddit / Handle, der abgefragt wurde)
    account: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Autor des Inhalts
    author_username: Mapped[str | None] = mapped_column(String(255), index=True)
    author_display_name: Mapped[str | None] = mapped_column(String(512))

    # Inhalt
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType), nullable=False, index=True
    )
    text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))  # "de", "en", …

    # Zeitstempel
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Engagement (denormalisiert für schnelle Queries)
    likes_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comments_count: Mapped[int] = mapped_column(BigInteger, default=0)
    shares_count: Mapped[int] = mapped_column(BigInteger, default=0)

    # Vollständiges Original-JSON
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Freie Metadaten (Hashtags, URLs, Medien-Typen, …)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        # Verhindert Duplikate beim erneuten Ingest
        UniqueConstraint("platform", "source_id", name="uq_platform_source"),
        # Volltext-ähnliche Suche über JSONB-Tags
        Index("ix_posts_meta_gin", "meta", postgresql_using="gin"),
        Index("ix_posts_raw_gin", "raw_data", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Post {self.platform.value}:{self.source_id} [{self.content_type.value}]>"
