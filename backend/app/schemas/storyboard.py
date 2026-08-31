from pydantic import BaseModel


class StoryboardScene(BaseModel):
    scene_number: int
    duration_seconds: float
    narration: str
    visual_prompt: str
    camera_motion: str
    caption: str
    transition: str
    sound_effect: str | None = None


class GeneratedStoryboard(BaseModel):
    scenes: list[StoryboardScene]
