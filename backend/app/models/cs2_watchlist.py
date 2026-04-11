from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CS2Watchlist(Base):
    """CS2 饰品自选监控 + 价格提醒"""
    __tablename__ = "cs2_watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("cs2_items.id"), nullable=False)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # above/below
    triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_cs2_watch_user_item"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "target_price": self.target_price,
            "alert_direction": self.alert_direction,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
