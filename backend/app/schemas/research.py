from pydantic import BaseModel, ConfigDict, Field


class GeneratedResearchItem(BaseModel):
    topic: str
    summary: str
    why_now: str
    trend_score: int = Field(ge=0, le=100)
    novelty_score: int = Field(ge=0, le=100)
    sources: list[str] = []


class GeneratedResearchList(BaseModel):
    items: list[GeneratedResearchItem]


class ResearchItemOut(BaseModel):
    id: int
    content_profile_id: int
    topic: str
    summary: str
    why_now: str
    trend_score: int
    novelty_score: int
    sources: list
    model_config = ConfigDict(from_attributes=True)
