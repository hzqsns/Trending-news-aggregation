from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base, JSONField


class HistoricalEvent(Base):
    __tablename__ = "historical_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    date_range: Mapped[str] = mapped_column(String(50), nullable=False)
    market_impact: Mapped[str] = mapped_column(String(20), nullable=False, default="mixed")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_metrics: Mapped[list | None] = mapped_column(JSONField, nullable=True, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_historical_event_category", "category"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "date_range": self.date_range,
            "market_impact": self.market_impact,
            "description": self.description,
            "key_metrics": self.key_metrics or [],
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
