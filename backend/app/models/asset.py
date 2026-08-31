from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Asset(Base):
    """A visual asset (image or video clip) backing one scene."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    scene_id: Mapped[int | None] = mapped_column(ForeignKey("scenes.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(500))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    license_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AudioAsset(Base):
    """A voiceover / music / sound-effect clip. Kept separate from visual
    Assets per the spec's entity list (section 8) -- different lifecycle
    (mixed into the render, not composited as frames)."""

    __tablename__ = "audio_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    scene_id: Mapped[int | None] = mapped_column(ForeignKey("scenes.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(100))
    path: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[float] = mapped_column(Float)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
