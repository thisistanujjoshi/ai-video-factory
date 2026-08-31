from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# ponytail: nested config (niche/audience/video/style/strategy/publishing/schedule)
# lives as JSON columns instead of ~7 join tables — nothing queries into these
# fields relationally yet. Normalize if that changes; validated at the API
# boundary by app.schemas.content_profile in the meantime.


class ContentProfile(Base):
    __tablename__ = "content_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    niche: Mapped[dict] = mapped_column(JSON)
    audience: Mapped[dict] = mapped_column(JSON)
    video: Mapped[dict] = mapped_column(JSON)
    style: Mapped[dict] = mapped_column(JSON)
    strategy: Mapped[dict] = mapped_column(JSON)
    publishing: Mapped[dict] = mapped_column(JSON)
    schedule: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
