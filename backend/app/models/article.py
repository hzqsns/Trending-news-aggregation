from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONField


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_pushed: Mapped[bool] = mapped_column(Boolean, default=False)
    importance: Mapped[int] = mapped_column(Integer, default=0)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_articles_category", "category"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_source", "source"),
        Index("ix_articles_importance", "importance"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "summary": self.summary,
            "image_url": self.image_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_pushed": self.is_pushed,
            "importance": self.importance,
            "sentiment": self.sentiment,
            "ai_analysis": self.ai_analysis,
            "tags": self.tags.split(",") if self.tags else [],
        }
