from datetime import date, datetime
from sqlalchemy import String, Text, Date, DateTime, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONField


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # economic | earnings | custom
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    # "08:30" UTC, optional
    event_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # high | medium | low
    importance: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    # source of the event: "manual" | "fred" | "alpha_vantage" | etc.
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="manual")
    # extra metadata (e.g. ticker symbol for earnings, indicator code for economic)
    meta: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_calendar_event_date", "event_date"),
        Index("ix_calendar_event_type", "event_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "event_type": self.event_type,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "event_time": self.event_time,
            "description": self.description,
            "importance": self.importance,
            "source": self.source,
            "meta": self.meta or {},
            "is_notified": self.is_notified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
