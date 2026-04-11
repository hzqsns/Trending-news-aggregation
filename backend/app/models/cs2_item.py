from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CS2Item(Base):
    """CS2 饰品元数据表（全局共享，不含 agent_key）"""
    __tablename__ = "cs2_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_hash_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # knife/gloves/rifle/pistol/smg/shotgun/sticker/case
    subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ak47/m4a4/awp/...
    rarity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    wear: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    steam_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_cs2_items_category", "category"),
        Index("ix_cs2_items_is_tracked", "is_tracked"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "market_hash_name": self.market_hash_name,
            "display_name": self.display_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "rarity": self.rarity,
            "wear": self.wear,
            "image_url": self.image_url,
            "steam_url": self.steam_url,
            "is_tracked": self.is_tracked,
        }
