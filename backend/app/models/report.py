from datetime import datetime, date

from sqlalchemy import String, Text, DateTime, Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONField


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_events: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    sentiment_data: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    suggestions: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("report_type", "report_date", name="uq_report_type_date"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_type": self.report_type,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "title": self.title,
            "content": self.content,
            "key_events": self.key_events,
            "sentiment_data": self.sentiment_data,
            "suggestions": self.suggestions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
