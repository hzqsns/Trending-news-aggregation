from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CS2PriceSnapshot(Base):
    """CS2 饰品价格时序快照（只增不改）"""
    __tablename__ = "cs2_price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("cs2_items.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="steam")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    volume: Mapped[int] = mapped_column(Integer, default=0)
    listings: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cs2_snap_item_time", "item_id", "snapshot_time"),
        Index("ix_cs2_snap_platform", "platform"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "platform": self.platform,
            "price": self.price,
            "currency": self.currency,
            "volume": self.volume,
            "listings": self.listings,
            "snapshot_time": self.snapshot_time.isoformat() if self.snapshot_time else None,
        }
