from pydantic import BaseModel


class ScriptScene(BaseModel):
    scene_number: int
    narration: str


class GeneratedScript(BaseModel):
    title: str
    hook: str
    narration: str
    estimated_duration_seconds: float
    cta: str
    engagement_question: str
    scenes: list[ScriptScene]
