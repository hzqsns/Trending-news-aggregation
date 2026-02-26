from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONField


class SentimentSnapshot(Base):
    __tablename__ = "sentiment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    overall_score: Mapped[int] = mapped_column(Integer, default=50)
    label: Mapped[str] = mapped_column(String(20), default="neutral")
    breakdown: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    news_volume: Mapped[int] = mapped_column(Integer, default=0)
    top_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "snapshot_time": self.snapshot_time.isoformat() if self.snapshot_time else None,
            "overall_score": self.overall_score,
            "label": self.label,
            "breakdown": self.breakdown,
            "news_volume": self.news_volume,
            "top_keywords": self.top_keywords.split(",") if self.top_keywords else [],
        }
