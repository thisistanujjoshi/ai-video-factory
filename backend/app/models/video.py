from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.video_state import VideoState


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_profile_id: Mapped[int] = mapped_column(ForeignKey("content_profiles.id"))
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("ideas.id"), nullable=True)
    script_id: Mapped[int | None] = mapped_column(ForeignKey("scripts.id"), nullable=True)
    state: Mapped[VideoState] = mapped_column(Enum(VideoState), default=VideoState.DRAFT)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rendered_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="video", order_by="Scene.scene_number", cascade="all, delete-orphan"
    )


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    scene_number: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float)
    narration: Mapped[str] = mapped_column(Text)
    visual_prompt: Mapped[str] = mapped_column(Text)
    camera_motion: Mapped[str] = mapped_column(String(100))
    caption: Mapped[str] = mapped_column(Text)
    transition: Mapped[str] = mapped_column(String(50))
    sound_effect: Mapped[str | None] = mapped_column(String(200), nullable=True)

    video: Mapped["Video"] = relationship(back_populates="scenes")
