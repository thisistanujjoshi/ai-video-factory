from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.publication import Publication


class Metric(Base):
    """One row per collected snapshot of one Publication's performance.
    Normalized columns are the common schema every platform maps into;
    `raw` keeps the platform's actual (mocked, for now) payload separately
    per spec section 33."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    snapshot_label: Mapped[str] = mapped_column(
        String(20)
    )  # "1h" | "6h" | "24h" | "48h" | "7d" | "manual"
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    followers_gained: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    publication: Mapped[Publication] = relationship()
