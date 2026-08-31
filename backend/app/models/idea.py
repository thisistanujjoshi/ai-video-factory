from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_profile_id: Mapped[int] = mapped_column(ForeignKey("content_profiles.id"))
    research_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_items.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    premise: Mapped[str] = mapped_column(Text)
    hook: Mapped[str] = mapped_column(Text)
    target_emotion: Mapped[str] = mapped_column(String(100))
    format: Mapped[str] = mapped_column(String(100))
    estimated_duration: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(50))
    scores: Mapped[dict] = mapped_column(JSON)
    overall_score: Mapped[float] = mapped_column(Float)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
