from datetime import date, datetime
from sqlalchemy import String, Float, Date, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MacroDataPoint(Base):
    __tablename__ = "macro_data_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(20), nullable=False)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mom: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("series_id", "data_date", name="uq_macro_series_date"),
        Index("ix_macro_series_id", "series_id"),
        Index("ix_macro_data_date", "data_date"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "series_id": self.series_id,
            "data_date": self.data_date.isoformat() if self.data_date else None,
            "value": self.value,
            "yoy": self.yoy,
            "mom": self.mom,
        }
