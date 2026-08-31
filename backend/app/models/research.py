from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResearchItem(Base):
    __tablename__ = "research_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_profile_id: Mapped[int] = mapped_column(ForeignKey("content_profiles.id"))
    topic: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    why_now: Mapped[str] = mapped_column(Text)
    trend_score: Mapped[int] = mapped_column(Integer)
    novelty_score: Mapped[int] = mapped_column(Integer)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
