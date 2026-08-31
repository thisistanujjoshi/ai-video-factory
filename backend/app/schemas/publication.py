from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.publication import PublicationStatus


class PublicationOut(BaseModel):
    id: int
    video_id: int
    platform: str
    status: PublicationStatus
    platform_metadata: dict
    scheduled_for: datetime | None
    published_at: datetime | None
    platform_ref: str | None
    error: str | None
    retry_count: int
    model_config = ConfigDict(from_attributes=True)


class ScheduleRequest(BaseModel):
    scheduled_for: datetime
