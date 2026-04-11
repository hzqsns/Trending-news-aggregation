from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONField


class CS2Prediction(Base):
    """CS2 饰品 AI 预测结果"""
    __tablename__ = "cs2_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("cs2_items.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # 7d/14d/30d
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # bullish/bearish/neutral
    up_prob: Mapped[float] = mapped_column(Float, nullable=False)
    flat_prob: Mapped[float] = mapped_column(Float, nullable=False)
    down_prob: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    predicted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    factors: Mapped[list | None] = mapped_column(JSONField, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cs2_pred_item_period_time", "item_id", "period", "generated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "period": self.period,
            "direction": self.direction,
            "up_prob": self.up_prob,
            "flat_prob": self.flat_prob,
            "down_prob": self.down_prob,
            "confidence": self.confidence,
            "predicted_price": self.predicted_price,
            "reasoning": self.reasoning,
            "factors": self.factors,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
