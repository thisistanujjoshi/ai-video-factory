from pydantic import BaseModel

from app.schemas.publication import PublicationOut
from app.schemas.video import VideoOut


class AutonomousCycleOut(BaseModel):
    video: VideoOut
    qa_passed: bool
    content_score: int
    auto_published: bool
    publications: list[PublicationOut]
