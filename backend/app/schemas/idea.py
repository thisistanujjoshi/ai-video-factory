from pydantic import BaseModel, ConfigDict, Field


class IdeaScores(BaseModel):
    curiosity: int = Field(ge=0, le=100)
    emotion: int = Field(ge=0, le=100)
    trend: int = Field(ge=0, le=100)
    novelty: int = Field(ge=0, le=100)
    shareability: int = Field(ge=0, le=100)
    production_cost: int = Field(ge=0, le=100)


class GeneratedIdea(BaseModel):
    title: str
    premise: str
    hook: str
    target_emotion: str
    format: str
    estimated_duration: int
    difficulty: str
    scores: IdeaScores


class GeneratedIdeaList(BaseModel):
    ideas: list[GeneratedIdea]


class IdeaOut(BaseModel):
    id: int
    content_profile_id: int
    research_item_id: int | None
    title: str
    premise: str
    hook: str
    target_emotion: str
    format: str
    estimated_duration: int
    difficulty: str
    scores: dict
    overall_score: float
    model_config = ConfigDict(from_attributes=True)
