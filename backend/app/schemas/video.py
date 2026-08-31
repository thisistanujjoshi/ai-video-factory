from pydantic import BaseModel, ConfigDict

from app.models.video_state import VideoState


class SceneOut(BaseModel):
    scene_number: int
    duration_seconds: float
    narration: str
    visual_prompt: str
    camera_motion: str
    caption: str
    transition: str
    sound_effect: str | None
    model_config = ConfigDict(from_attributes=True)


class VideoOut(BaseModel):
    id: int
    content_profile_id: int
    idea_id: int | None
    script_id: int | None
    state: VideoState
    title: str | None
    rendered_path: str | None
    scenes: list[SceneOut] = []
    model_config = ConfigDict(from_attributes=True)
