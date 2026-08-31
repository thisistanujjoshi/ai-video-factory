from pydantic import BaseModel, ConfigDict

from app.models.automation_mode import AutomationMode


class Niche(BaseModel):
    primary: str
    secondary: list[str] = []


class Audience(BaseModel):
    min_age: int
    max_age: int
    language: str = "English"


class VideoConfig(BaseModel):
    type: str = "short"
    min_duration_seconds: int = 45
    max_duration_seconds: int = 75
    aspect_ratio: str = "9:16"
    resolution: str = "1080x1920"


class Style(BaseModel):
    tone: str
    pacing: str
    narration: str
    visual_style: str


class Strategy(BaseModel):
    hook_types: list[str] = []


class Publishing(BaseModel):
    youtube: bool = True
    instagram: bool = True
    tiktok: bool = True


class Schedule(BaseModel):
    videos_per_day: int = 1


class ContentProfileCreate(BaseModel):
    name: str
    niche: Niche
    audience: Audience
    video: VideoConfig = VideoConfig()
    style: Style
    strategy: Strategy = Strategy()
    publishing: Publishing = Publishing()
    schedule: Schedule = Schedule()
    automation_mode: AutomationMode = AutomationMode.MANUAL


class ContentProfileOut(ContentProfileCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
