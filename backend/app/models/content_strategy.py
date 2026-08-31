from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentStrategy(Base):
    """One row per generated strategy for a profile. The most recent row
    (highest id / created_at) is "current" -- old ones stay around as
    history rather than being overwritten (spec section 55 versioning)."""

    __tablename__ = "content_strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_profile_id: Mapped[int] = mapped_column(ForeignKey("content_profiles.id"))
    best_topics: Mapped[list] = mapped_column(JSON, default=list)
    best_hook_types: Mapped[list] = mapped_column(JSON, default=list)
    recommended_duration: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_pacing: Mapped[str] = mapped_column(Text)
    recommended_posting_windows: Mapped[list] = mapped_column(JSON, default=list)
    avoid_patterns: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text)
    sample_size: Mapped[int] = mapped_column(Integer)
    patterns: Mapped[dict] = mapped_column(
        JSON
    )  # the computed stats this strategy was generated from
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
