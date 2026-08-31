from pydantic import BaseModel, Field

from app.schemas.video import VideoOut


class QAResult(BaseModel):
    approved: bool
    score: int = Field(ge=0, le=100)
    issues: list[str] = []
    recommendations: list[str] = []


class QAReportOut(BaseModel):
    video: VideoOut
    passed: bool
    technical_issues: list[str]
    content_score: int
    content_approved: bool
    content_issues: list[str]
    content_recommendations: list[str]
